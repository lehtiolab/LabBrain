"""Hot files and drift verification: which summaries are due a check against a file."""

import os
import re
from urllib.parse import unquote

from .files import join, read, write
from .frontmatter import (
    DRIFT_KEY,
    content_hash,
    drift_lines,
    fm_drift,
    fm_sources,
    set_fm_block,
    split_fm,
)
from .git import blob_text, changes, git_hashes, history, iso
from .index import RELATED_RE, index_targets
from .links import MDLINK_RE, outside_code
from .notes import agent_files, note_type
from .summaries import SUMMARY_TYPE, expected, now, summaries

RECHECK = 3


def citations(vault):
    """vault path -> {agent-written file: number of links to it}. A folder's index.md counts only
    through its related block; the root one counts whole (the map)."""
    refs = {}
    citers = {p: read(vault, p) for p in agent_files(vault)}
    citers["index.md"] = read(vault, "index.md")
    for d in index_targets(vault):
        rel = join(d, "index.md")
        if d and os.path.exists(os.path.join(vault, rel)):
            block = "\n".join(m.group(0) for m in RELATED_RE.finditer(read(vault, rel)))
            if block:
                citers[rel] = block
    for f, text in citers.items():
        here = os.path.dirname(f)

        def scan(s):
            for m in MDLINK_RE.finditer(s):
                url = m.group(3)
                if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
                    continue
                p = os.path.normpath(join(here, unquote(url.partition("#")[0])))
                refs.setdefault(p, {})[f] = refs.get(p, {}).get(f, 0) + 1
            return s

        outside_code(text, scan)
    return refs


def covers(vault):
    """vault path -> the summary that hashes it."""
    cover = {}
    for s in summaries(vault):
        sdir = os.path.dirname(s)
        for src in expected(vault, sdir)[0]:
            cover[join(sdir, src)] = s
    return cover


def changes_since(vault, rel, entry, cache):
    """How many times rel has changed since the version a drift_verification entry records:
    commits that changed it after that version, plus one for uncommitted edits."""
    cur = git_hashes(vault, [rel])[rel]
    if cur == entry.get("hash"):
        return 0
    hist = history(vault, rel, cache)
    dirty = 1 if not hist or hist[0][2] != cur else 0
    for i, (_, _, blob) in enumerate(hist):
        if blob == entry.get("hash"):
            return dirty + i
    # The checked version was never committed (it was edited again first): count the later commits.
    try:
        at = iso(entry.get("at") or "")
    except ValueError:
        return dirty + len(hist)
    return dirty + sum(1 for _, date, _ in hist if date > at)


def edits_since(vault, s, entry, cache):
    """How many times summary s has been edited since the check a drift_verification entry records:
    changes to its description or body (not frontmatter bookkeeping), committed or not."""
    want = entry.get("summary_hash")
    prev = content_hash(read(vault, s))
    if prev == want:
        return 0
    try:
        at = iso(entry.get("at") or "")
    except ValueError:
        at = None
    n = 0
    for _, date, blob in history(vault, s, cache):
        if blob is None:
            break
        h = content_hash(blob_text(vault, s, blob))
        if h != prev:
            n, prev = n + 1, h
        if h == want:
            return n
        if at and date <= at:  # the checked text was never committed (edited again first)
            break
    return max(n, 1)


def drift_checks(vault, p, s, refs, recheck, cache):
    """{file: (kind, entry, (changes to p, edits to the summary) since, due)} for the summary
    hashing p (s) and the files citing it.

    kind 'tag': a summary, whose drift_verification entry for p says when it was last checked; due
    when there is none, or when changes to p plus edits to the summary since then reach `recheck`.
    'record': a session summary, never checked. 'untagged': index.md (the map, related blocks) and
    any other agent-written file (an agent guide, a paper concept), checked whenever p is due.
    """
    out = {}
    for f in ([s] if s else []) + sorted(f for f in refs if f != s):
        kind = {SUMMARY_TYPE: "tag", "Session Summary": "record"}.get(
            note_type(vault, f), "untagged"
        )
        if kind != "tag":
            out[f] = (kind, None, None, None)
            continue
        here = os.path.dirname(f)
        entry = next(
            (
                e
                for e in fm_drift(split_fm(read(vault, f))[0])
                if os.path.normpath(join(here, e.get("resource", ""))) == p
            ),
            None,
        )
        n = (
            (changes_since(vault, p, entry, cache), edits_since(vault, f, entry, cache))
            if entry
            else None
        )
        out[f] = (kind, entry, n, n is None or sum(n) >= recheck)
    return out


def is_due(checks):
    """A hot file is due when one of its summaries is, or when no summary hashes or cites it."""
    tagged = [c for c in checks.values() if c[0] == "tag"]
    return not tagged or any(c[3] for c in tagged)


def hot(vault, days, least, recheck=RECHECK):
    """[(path, commits, dirty, covering summary or None, summary status, {citer: links},
    drift checks)], hottest first."""
    cache = {}
    cover = covers(vault)
    counts = changes(vault, days)
    refs = citations(vault)
    rows = []
    for p in cover:
        n, dirty = counts.get(p, (0, False))
        if n + dirty < least:
            continue
        s, status = cover.get(p), None
        if s:
            recorded = dict(fm_sources(split_fm(read(vault, s))[0]))
            r = os.path.relpath(p, os.path.dirname(s) or ".")
            status = (
                "stale: new"
                if r not in recorded
                else "current"
                if git_hashes(vault, [p])[p] == recorded[r]
                else "stale: changed"
            )
        cited = {f: k for f, k in refs.get(p, {}).items() if f != s}
        checks = drift_checks(vault, p, s, cited, recheck, cache)
        rows.append((p, n, dirty, s, status, cited, checks))
    return sorted(rows, key=lambda r: (-(r[1] + r[2]), r[0]))


def drift_stamp(vault, p, by, files=None, recheck=RECHECK):
    """Record a drift check of p in the given summaries, or in every summary due for p.
    Returns (stamped, refused): files that are not summaries can't hold the tag."""
    cache = {}
    if files is None:
        s = covers(vault).get(p)
        checks = drift_checks(vault, p, s, citations(vault).get(p, {}), recheck, cache)
        files = [f for f, c in checks.items() if c[0] == "tag" and c[3]]
    hist = history(vault, p, cache)
    new = {
        "hash": git_hashes(vault, [p])[p],
        "commit": hist[0][0] if hist else "none",
        "at": now(),
        "by": by,
    }
    stamped, refused = [], []
    for f in files:
        if note_type(vault, f) != SUMMARY_TYPE:
            refused.append(f)
            continue
        text = read(vault, f)
        here = os.path.dirname(f)
        entries = [
            e
            for e in fm_drift(split_fm(text)[0])
            if os.path.normpath(join(here, e.get("resource", ""))) != p
        ]
        entries.append(
            dict(new, resource=os.path.relpath(p, here or "."), summary_hash=content_hash(text))
        )
        entries.sort(key=lambda e: e["resource"])
        write(vault, f, set_fm_block(text, DRIFT_KEY, drift_lines(entries)))
        stamped.append(f)
    return stamped, refused
