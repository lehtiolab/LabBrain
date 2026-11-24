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
from .summaries import expected, summaries

HIERARCHY = join(MAPS, "hierarchy.yaml")
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


def hierarchy(vault):
    """The wiki as a tree: its root index.md, then each folder summary under the summary of the
    folder above it. A summary's links are the other summaries its text links to, through their
    notes or directly, and the files it links to that no summary covers. Links to its own notes,
    its parent and its children are left out: the tree shows those already."""
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

    root = {"title": os.path.basename(os.path.abspath(vault)), "path": "index.md"}
    roots = [s for s in sums if s not in parent]
    return dict(root, children=[node(s) for s in roots]) if roots else root


def write_hierarchy(vault):
    """Write the tree to _maps/hierarchy.yaml; returns its path."""
    text = yaml.safe_dump(hierarchy(vault), sort_keys=False, allow_unicode=True, width=100)
    return save(vault, HIERARCHY, HEADER + text)
