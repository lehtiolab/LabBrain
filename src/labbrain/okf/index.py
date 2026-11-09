"""The generated index.md listings, keeping their agent-maintained map and related blocks."""

import os
import re
from urllib.parse import unquote

from .files import RESERVED, has_notes, is_repo_root, join, listdir, read, walk, write
from .frontmatter import fm_get, split_fm
from .links import href
from .summaries import parent_summary, summaries, summary_in

OKF_VERSION = "0.2"


# Agent-maintained blocks of an index.md, which `index` keeps as they are: the vault map (root only)
# and a folder's related links (the links its notes ask agents for, kept out of the notes).
KEEP_RE = re.compile(r"^<!-- (map|related):start -->[ \t]*$.*?^<!-- \1:end -->[ \t]*$", re.M | re.S)


RELATED_RE = re.compile(
    r"^<!-- related:start -->[ \t]*$.*?^<!-- related:end -->[ \t]*$", re.M | re.S
)


IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".tif", ".tiff", ".bmp"}


def contents_descriptions(vault):
    """vault path -> one-line description, from every summary's Contents section."""
    out = {}
    for spath in summaries(vault):
        _, body = split_fm(read(vault, spath))
        m = re.search(r"^## Contents[ \t]*\n(.*?)(?=^#{1,2} |\Z)", body, re.M | re.S)
        if not m:
            continue
        sdir = os.path.dirname(spath)
        for line in m.group(1).splitlines():
            lm = re.match(r"\s*[-*]\s+(.+?)\s+—\s+(.+?)\s*$", line)
            if not lm:
                continue
            head, desc = lm.groups()
            if re.sub(r"\[[^\]]*\]\([^)]*\)|\([^)]*\)|`[^`]*`|[,\s]|and", "", head):
                continue  # not a plain list of files, e.g. "Child summaries: ..."
            desc = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", desc)
            for t in re.finditer(r"\]\(([^)#\s]+)[^)]*\)|`([^`]+)`", head):
                p = os.path.normpath(join(sdir, unquote(t.group(1) or t.group(2))))
                if os.path.basename(p) == "index.md":  # a subfolder, linked through its index
                    p = os.path.dirname(p)
                if os.path.exists(os.path.join(vault, p)):
                    out.setdefault(p, desc)
    return out


def meta(vault, rel):
    """(title, description) of a note from its frontmatter."""
    fm, body = split_fm(read(vault, rel))
    return fm_get(fm, "title"), fm_get(fm, "description")


def entry(title, url, desc=None):
    return "* [%s](%s)%s" % (title, url, " - " + desc if desc else "")


def render_index(vault, d, descs, keep=None):
    """The index.md of folder d; keep is its agent-maintained blocks, appended as they are."""
    dirs, files = listdir(vault, d)
    out = []
    if is_repo_root(vault, d):
        out += ["---", 'okf_version: "%s"' % OKF_VERSION, "---", ""]

    s = summary_in(vault, d)
    cover = s or parent_summary(vault, d)
    if cover:
        title, desc = meta(vault, cover)
        if not s:
            desc = "Covers this folder. " + (desc or "")
        out += [
            "# Summary",
            "",
            entry(title or os.path.basename(cover)[:-3], href(cover, d), desc),
            "",
        ]

    notes = [
        join(d, f) for f in files if f.endswith(".md") and f not in RESERVED and join(d, f) != s
    ]
    if notes:
        out += ["# Notes", ""]
        for n in notes:
            title, desc = meta(vault, n)
            out.append(entry(title or os.path.basename(n)[:-3], href(n, d), desc or descs.get(n)))
        out.append("")

    subs = [join(d, e) for e in dirs if has_notes(vault, join(d, e))]
    if subs:
        out += ["# Subfolders", ""]
        for p in subs:
            cs = summary_in(vault, p)
            out.append(
                entry(
                    os.path.basename(p),
                    href(join(p, "index.md"), d),
                    meta(vault, cs)[1] if cs else descs.get(p),
                )
            )
        out.append("")

    others = [join(d, f) for f in files if not f.endswith(".md")]
    for e in dirs:
        if not has_notes(vault, join(d, e)):
            others += [join(sd, f) for sd, _, fs in walk(vault, join(d, e)) for f in fs]
    others = [o for o in others if os.path.splitext(o)[1].lower() not in IMAGE_EXT]
    if others:
        out += ["# Other files", ""]
        out += [entry(os.path.relpath(o, d or "."), href(o, d), descs.get(o)) for o in others]
        out.append("")

    text = "\n".join(out).rstrip("\n") + "\n"
    return text + "\n" + keep + "\n" if keep else text


def index_targets(vault):
    return [d for d, _, _ in walk(vault) if has_notes(vault, d)]


def build_indexes(vault, dry=False):
    """Write (or with dry=True, list) every index.md that differs from its rendering."""
    descs = contents_descriptions(vault)
    changed = []
    for d in index_targets(vault):
        rel = join(d, "index.md")
        old = read(vault, rel) if os.path.exists(os.path.join(vault, rel)) else None
        keep = "\n\n".join(m.group(0) for m in KEEP_RE.finditer(old or ""))
        new = render_index(vault, d, descs, keep or None)
        if new != old:
            changed.append(rel)
            if not dry:
                write(vault, rel, new)
    return changed
