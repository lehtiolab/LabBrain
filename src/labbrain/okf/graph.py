"""The wiki as a graph: each markdown file a node; links, summaries and their subfolders the edges.

A cache: code builds it from the wiki, nobody edits it, and git ignores it (docs/usage.md).
"""

import json
import os
import re
from urllib.parse import unquote

from .canvas import save
from .files import MAPS, RESERVED, join, md_files, read
from .frontmatter import fm_get, fm_list, h1, split_fm
from .git import git_hashes
from .links import MDLINK_RE, WIKI_RE, name_index, outside_code, resolve
from .summaries import expected, summaries

GRAPH, CACHE = join(MAPS, "graph.json"), join(MAPS, "graph-cache.json")
SCHEME = re.compile(r"[a-z][a-z0-9+.-]*:", re.I)
FIELDS = ("type", "title", "description", "tags", "topics", "annotate")
CACHE_VERSION = 2  # what parse() returns; a cache from another version is rebuilt


def parse(text):
    """What the graph needs from a file's text: header fields, and links as written. Links are
    resolved when the graph is built, since what a name points to depends on the other files."""
    fm, body = split_fm(text)
    refs = []

    def scan(s):
        for m in WIKI_RE.finditer(s):
            name = m.group(2).partition("|")[0].partition("#")[0]
            if name:
                refs.append(["name", name])
        for m in MDLINK_RE.finditer(s):
            url = m.group(3)
            if not SCHEME.match(url) and not url.startswith("#"):
                refs.append(["path", unquote(url.partition("#")[0])])
        return s

    outside_code(body, scan)
    fields = {
        "type": fm_get(fm, "type"),
        "title": fm_get(fm, "title") or h1(body),
        "description": fm_get(fm, "description"),
        "tags": fm_list(fm, "tags"),
        "topics": fm_list(fm, "topics"),
        "annotate": (fm_get(fm, "annotate") or "").lower() == "true",  # the author's consent
    }
    return {k: v for k, v in fields.items() if v}, refs


def target(vault, idx, kind, ref, here):
    """The wiki file a link points to, the way Obsidian resolves it; None if there is none."""
    if kind == "path":
        p = os.path.normpath(join(here, ref))
        if os.path.isfile(os.path.join(vault, p)):
            return p
        ref = ref.lstrip("/")
    return resolve(idx, ref, here)


def build_graph(vault, cache):
    """(graph, cache for the next build). cache maps a file's git blob hash to what parse() found
    in it; a file whose hash is there isn't read again."""
    files = [p for p in md_files(vault) if os.path.basename(p) not in RESERVED]
    hashes = git_hashes(vault, files)
    parsed = {h: cache.get(h) or parse(read(vault, p)) for p, h in hashes.items()}
    idx, ids = name_index(vault), set(files)
    nodes, edges = [], set()
    for p in sorted(files):
        fields, refs = parsed[hashes[p]]
        stem = os.path.splitext(os.path.basename(p))[0]
        nodes.append(
            {"id": p, **dict(fields, title=fields.get("title") or stem), "hash": hashes[p]}
        )
        for kind, ref in refs:
            t = target(vault, idx, kind, ref, os.path.dirname(p))
            if t in ids and t != p:
                edges.add((p, t, "link"))
    for s in summaries(vault):
        sdir = os.path.dirname(s)
        sources, kids = expected(vault, sdir)
        edges |= {(s, join(sdir, f), "covers") for f in sources if join(sdir, f) in ids}
        edges |= {(s, join(sdir, c), "child") for c in kids}
    graph = {
        "title": os.path.basename(os.path.abspath(vault)),
        "nodes": [{k: n[k] for k in ("id", *FIELDS, "hash") if k in n} for n in nodes],
        "edges": [{"from": a, "to": b, "kind": k} for a, b, k in sorted(edges)],
    }
    return graph, parsed


def load_cache(vault):
    """The per-file cache from the last build; empty if there is none or it can't be used."""
    try:
        saved = json.loads(read(vault, CACHE))
    except (OSError, ValueError):
        return {}
    if not isinstance(saved, dict) or saved.get("version") != CACHE_VERSION:
        return {}
    cache = saved.get("files")
    ok = isinstance(cache, dict) and all(
        isinstance(v, list) and len(v) == 2 and isinstance(v[0], dict) and isinstance(v[1], list)
        for v in cache.values()
    )
    return cache if ok else {}


def dump(data):
    return json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def write_graph(vault):
    """Bring _maps/graph.json up to date. Returns (graph, number of files read)."""
    cache = load_cache(vault)
    graph, parsed = build_graph(vault, cache)
    save(vault, GRAPH, dump(graph))
    save(vault, CACHE, dump({"version": CACHE_VERSION, "files": dict(sorted(parsed.items()))}))
    return graph, len(set(parsed) - set(cache))
