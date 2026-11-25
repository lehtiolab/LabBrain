"""The wiki as a graph: each ingested markdown file a node; links, summaries and their subfolders
the edges, and the links code proposes between files that share topics.

A cache: code builds it from the wiki, nobody edits it, and git ignores it (docs/usage.md). The
proposed links people turn down are not a cache: they are kept in _maps/rejected.jsonl.
"""

import json
import os
import re
from collections import Counter
from itertools import combinations
from urllib.parse import unquote

from .canvas import save
from .files import MAPS, RESERVED, join, md_files, read
from .frontmatter import fm_get, fm_list, h1, split_fm
from .git import git_hashes
from .links import MDLINK_RE, WIKI_RE, name_index, outside_code, resolve
from .summaries import expected, now, summaries
from .topics import as_topic, topic_names

GRAPH, CACHE = join(MAPS, "graph.json"), join(MAPS, "graph-cache.json")
REJECTED = join(MAPS, "rejected.jsonl")
# ponytail: files are related when they share this many topics, by exact name. Narrower topics,
# words in common and relations only a model can see are on the wish list (AGENT.md).
SHARED = 2
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


def within(a, b):
    """True if one file's folder holds the other's; the wiki's root holds every file."""
    da, db = (os.path.dirname(p) + os.sep for p in (a, b))
    return os.sep in (da, db) or da.startswith(db) or db.startswith(da)


def proposed(nodes, edges, rejected, topics):
    """The links code proposes: files that share SHARED topics or more, vetoed ones aside, with no
    edge between them and neither in the other's folder (the summary tree already relates those),
    unless a person turned the pair down. As (from, to, "proposed"), from before to."""
    joined = {tuple(sorted(e[:2])) for e in edges}
    by_topic = {}
    for n in nodes:
        for t in n.get("topics", []):
            if topics.get(t, {}).get("status") != "vetoed":
                by_topic.setdefault(t, []).append(n["id"])
    shared = Counter(pair for ids in by_topic.values() for pair in combinations(sorted(ids), 2))
    return {
        (a, b, "proposed")
        for (a, b), k in shared.items()
        if k >= SHARED and (a, b) not in joined and (a, b) not in rejected and not within(a, b)
    }


def build_graph(vault, cache, rejected, topics):
    """(graph, cache for the next build).

    Only ingested files are nodes: a header with a type, and a listing in their folder's
    index.md. The others are the graph's `waiting` list. A node's topics are named as the
    vocabulary, topics, names them, so a topic merged into another as its synonym needs no file
    rewritten. cache maps a file's git blob hash to what parse() found in it; a file whose hash is
    there isn't read again. rejected: the proposed links people turned down, as sorted pairs.
    """
    every = md_files(vault)
    files = [p for p in every if os.path.basename(p) not in RESERVED]
    indexes = [p for p in every if os.path.basename(p) == "index.md"]
    hashes = git_hashes(vault, files + indexes)
    parsed = {h: cache.get(h) or parse(read(vault, p)) for p, h in hashes.items()}
    # Listed: linked from the index.md of its own folder. A link there to another folder's file
    # (the map, a related block, the summary over a folder without one) lists nothing.
    listed = set()
    for i in indexes:
        here = os.path.dirname(i)
        found = (os.path.normpath(join(here, r)) for k, r in parsed[hashes[i]][1] if k == "path")
        listed |= {t for t in found if os.path.dirname(t) == here}
    ids = {p for p in files if p in listed and parsed[hashes[p]][0].get("type")}
    idx, named = name_index(vault), topic_names(topics)
    nodes, edges = [], set()
    for p in sorted(ids):
        fields, refs = parsed[hashes[p]]
        if "topics" in fields:
            words = (named.get(as_topic(t), as_topic(t)) for t in fields["topics"])
            fields = dict(fields, topics=list(dict.fromkeys(words)))
        stem = os.path.splitext(os.path.basename(p))[0]
        nodes.append(
            {"id": p, **dict(fields, title=fields.get("title") or stem), "hash": hashes[p]}
        )
        for kind, ref in refs:
            t = target(vault, idx, kind, ref, os.path.dirname(p))
            if t in ids and t != p:
                edges.add((p, t, "link"))
    for s in summaries(vault):
        if s not in ids:
            continue
        sdir = os.path.dirname(s)
        sources, kids = expected(vault, sdir)
        edges |= {(s, join(sdir, f), "covers") for f in sources if join(sdir, f) in ids}
        edges |= {(s, join(sdir, c), "child") for c in kids if join(sdir, c) in ids}
    edges |= proposed(nodes, edges, rejected, topics)
    graph = {
        "title": os.path.basename(os.path.abspath(vault)),
        "nodes": [{k: n[k] for k in ("id", *FIELDS, "hash") if k in n} for n in nodes],
        "edges": [{"from": a, "to": b, "kind": k} for a, b, k in sorted(edges)],
        "waiting": sorted(set(files) - ids),
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


class BadRejection(Exception):
    """A line of _maps/rejected.jsonl that isn't a rejection."""

    def __init__(self, path, line, text):
        self.path, self.line, self.text = path, line, text
        super().__init__(
            'bad record in %s, line %d: %s (wanted {"at": …, "by": …, "rejected": [FILE, FILE]})'
            % (path, line, text)
        )


def load_rejected(vault):
    """The proposed links people turned down, as sorted pairs of paths."""
    try:
        lines = read(vault, REJECTED).splitlines()
    except FileNotFoundError:
        return set()
    out = set()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            pair = json.loads(line)["rejected"]
        except (ValueError, KeyError, TypeError):
            pair = None
        if not (
            isinstance(pair, list) and len(pair) == 2 and all(isinstance(p, str) for p in pair)
        ):
            raise BadRejection(REJECTED, i, line)
        out.add(tuple(sorted(pair)))
    return out


def reject(vault, pair, by, at=None):
    """Record that by turned down the proposed link between the two files of pair. Appended,
    never rewritten, so a cut-off write loses one record at most."""
    line = json.dumps({"at": at or now(), "by": by, "rejected": sorted(pair)}, ensure_ascii=False)
    if not os.path.exists(os.path.join(vault, REJECTED)):
        save(vault, REJECTED, line + "\n")
        return
    with open(os.path.join(vault, REJECTED), "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


def write_graph(vault, rejected, topics):
    """Bring _maps/graph.json up to date. Returns (graph, number of files read)."""
    cache = load_cache(vault)
    graph, parsed = build_graph(vault, cache, rejected, topics)
    save(vault, GRAPH, dump(graph))
    save(vault, CACHE, dump({"version": CACHE_VERSION, "files": dict(sorted(parsed.items()))}))
    return graph, len(set(parsed) - set(cache))
