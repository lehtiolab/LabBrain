"""Links: wikilinks to relative links, broken links, hashes carried past link-only edits."""

import os
import re
from urllib.parse import quote, unquote

from .files import join, read, text_files, walk, write
from .frontmatter import (
    DRIFT_KEY,
    content_hash,
    drift_lines,
    fm_drift,
    fm_sources,
    split_fm,
    with_fm,
)
from .git import git_hashes
from .summaries import assemble, source_lines, summaries

CODE_RE = re.compile(r"(```.*?```|`[^`\n]*`)", re.S)


WIKI_RE = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")


MDLINK_RE = re.compile(r"(!?)\[((?:[^\]\n]|\\\])*)\]\(([^)\s]+)\)")


def outside_code(text, fn):
    parts = CODE_RE.split(text)
    return "".join(p if i % 2 else fn(p) for i, p in enumerate(parts))


def name_index(vault):
    """Obsidian-style link names -> vault-relative paths."""
    idx = {}
    for d, _, files in walk(vault):
        for f in files:
            p = join(d, f)
            idx.setdefault(f, []).append(p)
            if f.endswith(".md"):
                idx.setdefault(f[:-3], []).append(p)
    return idx


def resolve(idx, name, from_dir):
    """Resolve an Obsidian link target the way Obsidian does (closest match wins)."""
    name = name.strip()
    cands = idx.get(os.path.basename(name), [])
    if "/" in name:
        cands = [c for c in cands if c.endswith(name) or c.endswith(name + ".md")]
    if not cands:
        return None
    return sorted(
        cands, key=lambda c: (os.path.dirname(c) != from_dir, not c.startswith(from_dir), len(c))
    )[0]


def href(target, from_dir, heading=None):
    url = quote(os.path.relpath(target, from_dir or "."), safe="/")
    return url + ("#" + quote(heading, safe=":,'") if heading else "")


def convert_links(vault, rel, text, idx=None):
    """Wikilinks and unresolvable relative links -> relative markdown links.

    Returns (new_text, unresolved_names).
    """
    idx = idx or name_index(vault)
    here = os.path.dirname(rel)
    missing = []

    def wiki(m):
        bang, inner = m.groups()
        target, _, alias = inner.partition("|")
        name, _, heading = target.partition("#")
        if not name:
            return "%s[%s](#%s)" % (bang, alias or heading, quote(heading, safe=":,'"))
        path = resolve(idx, name, here)
        if not path:
            missing.append(name)
            return m.group(0)
        if bang:  # an embed's alias is its display size: ![name|300](path)
            text_ = name + ("|" + alias if alias else "")
        else:
            text_ = alias or (name + (" § " + heading if heading else ""))
        return "%s[%s](%s)" % (bang, text_, href(path, here, heading or None))

    def md(m):
        bang, label, url = m.groups()
        if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
            return m.group(0)
        path, _, anchor = url.partition("#")
        if os.path.exists(os.path.join(vault, here, unquote(path))):
            return m.group(0)
        found = resolve(idx, unquote(path).lstrip("/"), here)
        if not found:
            missing.append(unquote(path))
            return m.group(0)
        return "%s[%s](%s)" % (bang, label, href(found, here) + ("#" + anchor if anchor else ""))

    return outside_code(text, lambda s: MDLINK_RE.sub(md, WIKI_RE.sub(wiki, s))), missing


def carry_hashes(vault, before, before_content=None):
    """After a link-only edit, move each summary's recorded hash to its source's new hash.

    Only where the record matched the file before the edit, so real staleness survives.
    before_content (summary -> content_hash before the edit) does the same for the summary_hash
    of its drift_verification entries, so a link fixed in the summary itself isn't an edit.
    Returns the summaries that changed.
    """
    after = git_hashes(vault, text_files(vault))
    updated = []

    def carried(f, h):
        return after[f] if before.get(f) == h and after.get(f, h) != h else h

    for s in summaries(vault):
        text = read(vault, s)
        fm, body = split_fm(text)
        sdir = os.path.dirname(s)
        old_c, new_c = (before_content or {}).get(s), content_hash(text)
        pairs = [(r, carried(join(sdir, r), h)) for r, h in fm_sources(fm)]
        drift = []
        for e in fm_drift(fm):
            f = os.path.normpath(join(sdir, e.get("resource", "")))
            if not os.path.exists(os.path.join(vault, f)):
                # the file was deleted or moved: drop its entry (scan checks a new path afresh)
                continue
            e2 = dict(e, hash=carried(f, e.get("hash")))
            if old_c and e.get("summary_hash") == old_c:
                e2["summary_hash"] = new_c
            drift.append(e2)
        managed = {}
        if pairs != fm_sources(fm):
            managed["sources"] = source_lines(pairs)
        if drift != fm_drift(
            fm
        ):  # a drift check of the old version still holds after a link-only edit
            # no lines once the last record is dropped: assemble() then removes the key
            managed[DRIFT_KEY] = drift_lines(drift) if drift else []
        if managed:
            write(vault, s, with_fm(assemble(fm, managed, body), body))
            updated.append(s)
    return updated


def link_problems(vault, rel, broken=True):
    """Wikilinks, and (with broken=True) broken relative markdown links, in a file."""
    text = read(vault, rel)
    here = os.path.dirname(rel)
    found = []

    def scan(s):
        for m in WIKI_RE.finditer(s):
            found.append("wikilink " + m.group(0))
        for m in MDLINK_RE.finditer(s if broken else ""):
            url = m.group(3)
            if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
                continue
            if not os.path.exists(os.path.join(vault, here, unquote(url.partition("#")[0]))):
                found.append("broken " + url)
        return s

    outside_code(text, scan)
    return found
