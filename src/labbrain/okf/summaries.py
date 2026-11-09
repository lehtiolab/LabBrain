"""Folder summaries: what each should record, staleness, and stamping provenance."""

import os
from datetime import datetime, timezone

from .files import RESERVED, TEXT_EXT, is_repo_root, join, listdir, read, walk, write
from .frontmatter import fm_blocks, fm_list, fm_sources, h1, split_fm, with_fm, ys
from .git import git_hashes

HASH_METHOD = "git hash-object"


SUMMARY_TYPE = "Folder Summary"


# Frontmatter key order for summaries; unknown keys keep their place after these.
CANON = [
    "type",
    "title",
    "description",
    "resource",
    "tags",
    "status",
    "stale_after",
    "generated",
    "verified",
    "drift_verification",
    "parent",
    "children",
    "hash_method",
    "sources",
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summary_in(vault, d):
    _, files = listdir(vault, d)
    found = [f for f in files if f.endswith("_summary.md")]
    if not found:
        return None
    own = os.path.basename(d) + "_summary.md"
    return join(d, own if own in found else found[0])


def summaries(vault):
    return [s for s in (summary_in(vault, d) for d, _, _ in walk(vault)) if s]


def expected(vault, sdir):
    """(sources, children) a summary of folder sdir should record.

    sources: every text file in the folder, plus files in subfolders that have no summary
    of their own; children: the summaries of subfolders that do. Paths are relative to sdir.
    """
    sources, children = [], []

    def visit(d, prefix):
        dirs, files = listdir(vault, d)
        for f in files:
            if (
                os.path.splitext(f)[1].lower() in TEXT_EXT
                and f not in RESERVED
                and not f.endswith("_summary.md")
            ):
                sources.append(join(prefix, f))
        for e in dirs:
            p = join(d, e)
            if is_repo_root(vault, p):
                continue
            s = summary_in(vault, p)
            if s:
                children.append(join(prefix, e, os.path.basename(s)))
            else:
                visit(p, join(prefix, e))

    visit(sdir, "")
    return sorted(sources), sorted(children)


def parent_summary(vault, sdir):
    d = sdir
    while not is_repo_root(vault, d):
        d = os.path.dirname(d)
        s = summary_in(vault, d)
        if s:
            return s
    return None


def staleness(vault, spath):
    """List of (kind, detail) problems; empty when the summary is current."""
    fm, _ = split_fm(read(vault, spath))
    sdir = os.path.dirname(spath)
    recorded = dict(fm_sources(fm))
    srcs, kids = expected(vault, sdir)
    hashes = git_hashes(vault, [join(sdir, s) for s in srcs])
    problems = []
    for s in srcs:
        if s not in recorded:
            problems.append(("new", s))
        elif hashes[join(sdir, s)] != recorded[s]:
            problems.append(("changed", s))
    problems += [("removed", s) for s in recorded if s not in srcs]
    if sorted(fm_list(fm, "children")) != kids:
        problems.append(("children", ", ".join(kids) or "none"))
    return problems


def stamp(vault, spath, by, at=None):
    """Rewrite a summary's provenance block from the files on disk."""
    text = read(vault, spath)
    fm, body = split_fm(text)
    sdir = os.path.dirname(spath)
    srcs, kids = expected(vault, sdir)
    hashes = git_hashes(vault, [join(sdir, s) for s in srcs])
    parent = parent_summary(vault, sdir)
    managed = {
        "generated": ["generated: { by: %s, at: %s }" % (ys(by), at or now())],
        "parent": ["parent: " + ys(os.path.relpath(parent, sdir or "."))] if parent else None,
        "children": ["children:"] + ["  - " + ys(c) for c in kids] if kids else None,
        "hash_method": ["hash_method: " + HASH_METHOD],
        "sources": source_lines([(s, hashes[join(sdir, s)]) for s in srcs]),
    }
    write(vault, spath, with_fm(assemble(fm, managed, body), body))


def source_lines(pairs):
    """The `sources` block: one flow mapping per file, with its git blob hash."""
    return (
        ["sources:"] + ["  - { resource: %s, hash: %s }" % (ys(r), h) for r, h in pairs]
        if pairs
        else ["sources: []"]
    )


def assemble(fm, managed, body):
    """Frontmatter lines in canonical order: managed keys replaced, other keys kept."""
    blocks = [b for b in fm_blocks(fm or "") if b[0]]
    have = {k: lines for k, lines in blocks}
    have.setdefault("type", ["type: " + SUMMARY_TYPE])
    if "title" not in have and h1(body):
        have["title"] = ["title: " + ys(h1(body))]
    for k, lines in managed.items():
        if lines:
            have[k] = lines
        else:
            have.pop(k, None)
    out = []
    for k in CANON:
        if k in have:
            out += [line for line in have[k] if line.strip()]
    for k, lines in blocks:
        if k not in CANON and k in have:
            out += [line for line in lines if line.strip()]
    return [line.rstrip() for line in out]
