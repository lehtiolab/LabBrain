"""The folder summaries as one tree, with the links their text makes to other parts of the wiki."""

import os
import re
from urllib.parse import unquote

import yaml

from .canvas import save
from .drift import covers
from .files import MAPS, join, read
from .frontmatter import fm_get, split_fm
from .links import MDLINK_RE, outside_code
from .summaries import expected, summaries, summary_in

HEADER = (
    "# Written by `labbrain hierarchy` from the folder summaries, and rewritten on every run.\n"
)


def link_targets(vault, rel):
    """The wiki files a file's text links to, in order, each once. Broken links are left out."""
    here, found = os.path.dirname(rel), []

    def scan(s):
        for m in MDLINK_RE.finditer(s):
            url = m.group(3)
            if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
                continue
            p = os.path.normpath(join(here, unquote(url.partition("#")[0])))
            if os.path.isfile(os.path.join(vault, p)):
                found.append(p)
        return s

    outside_code(split_fm(read(vault, rel))[1], scan)
    return list(dict.fromkeys(found))


def hierarchy(vault, top=""):
    """The summaries in folder top (the whole wiki by default) as a tree, each under the summary
    of the folder above it.

    The tree's top is top's own summary, when every other summary in top sits under it; else the
    folder itself, with its index.md. A summary's links are the other summaries its text links
    to, through their notes or directly, inside top or not, and the files it links to that no
    summary covers. Links to its own notes, its parent and its children are left out: the tree
    shows those already."""
    sums = summaries(vault)
    cover = covers(vault)
    kids = {
        s: [join(os.path.dirname(s), c) for c in expected(vault, os.path.dirname(s))[1]]
        for s in sums
    }
    parent = {c: s for s in sums for c in kids[s]}

    def node(s):
        fm = split_fm(read(vault, s))[0]
        out = {"title": fm_get(fm, "title") or s, "path": s}
        if fm_get(fm, "description"):
            out["description"] = fm_get(fm, "description")
        near = {s, parent.get(s), *kids[s]}
        links = [t if t in kids else cover.get(t, t) for t in link_targets(vault, s)]
        links = [t for t in dict.fromkeys(links) if t not in near]
        if links:
            out["links"] = links
        if kids[s]:
            out["children"] = [node(c) for c in kids[s]]
        return out

    inside = {s for s in sums if not top or s.startswith(top + os.sep)}
    roots = [s for s in sums if s in inside and parent.get(s) not in inside]
    if roots and roots == [summary_in(vault, top)]:
        return node(roots[0])
    folder = {"title": os.path.basename(os.path.abspath(os.path.join(vault, top)))}
    if os.path.isfile(os.path.join(vault, top, "index.md")):
        folder["path"] = join(top, "index.md")
    return dict(folder, children=[node(s) for s in roots]) if roots else folder


def write_hierarchy(vault, top=""):
    """Write the tree of folder top to _maps/<top>/hierarchy.yaml; returns its path."""
    text = yaml.safe_dump(hierarchy(vault, top), sort_keys=False, allow_unicode=True, width=100)
    return save(vault, join(MAPS, top, "hierarchy.yaml"), HEADER + text)
