"""Search the wiki's graph, cheapest first: the files' headers, then their full text, then the
links around what was found. Code only: no model, and only the full-text step reads files."""

import re

from .files import read

HEADER = ("title", "description", "id")  # where step 1 looks for the words, in this order


def meanings(query, topics):
    """(words, topics): the query in lower case, plus what the vocabulary says it also means: the
    synonyms of a topic it names, and its narrower topics with theirs."""
    q = " ".join(query.split()).lower()
    named = [n for n, t in topics.items() if q in [n.lower(), *(s.lower() for s in t["synonyms"])]]
    words, seen, todo = {q}, set(), named
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            words |= {name.lower(), *(s.lower() for s in topics[name]["synonyms"])}
            todo = todo + topics[name]["narrower"]
    return sorted(words), sorted(seen)


def finder(words):
    """A regex for any of the words, each from the start of a word: "tomato" finds Tomatoes."""
    return re.compile("|".join(r"\b" + re.escape(w) for w in sorted(words, key=len, reverse=True)))


def header_hits(nodes, words, topics):
    """Step 1: {id: where it matched} for the files whose header names the words."""
    find, names = finder(words), {*words, *(t.lower() for t in topics)}
    hits = {}
    for n in nodes:
        where = next((k for k in HEADER if find.search(n.get(k, "").lower())), None)
        if not where:
            labels = [x.lower() for k in ("topics", "tags") for x in n.get(k, [])]
            where = next((k for k in ("topics", "tags") if names & set(labels)), None)
        if where:
            hits[n["id"]] = "path" if where == "id" else where
    return hits


def text_hits(vault, nodes, words, skip):
    """Step 2: {id: number of matches} for the files whose text has the words, most first."""
    # ponytail: reads every file; an SQLite FTS5 index (updated by blob hash) when that gets slow.
    find, counts = finder(words), {}
    for n in nodes:
        if n["id"] not in skip:
            k = len(find.findall(read(vault, n["id"]).lower()))
            if k:
                counts[n["id"]] = k
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def search(vault, graph, query, topics, depth=1, text=False):
    """The part of the graph a query finds, in the graph's own format, plus a `filter` saying how.

    Step 1 finds files by their header (title, description, path, tags, topics), with the
    vocabulary's synonyms and narrower topics. Step 2, the full text, runs when step 1 finds
    nothing, or when text is set. Step 3 follows links up to depth from what was found, and adds
    the summaries that cover the files found. A hit has `hit` (where it matched); a file reached
    by links has `distance`; a summary added for context has `context`. A full-text hit also has
    `matches`, the number of times the words appear.
    """
    words, named = meanings(query, topics)
    nodes = {n["id"]: n for n in graph["nodes"]}
    found = header_hits(graph["nodes"], words, named)
    step = 1 if found else 0
    if text or not found:
        more = text_hits(vault, graph["nodes"], words, found)
        found.update({p: ("text", k) for p, k in more.items()})
        step = 2 if more else step
    near = {}
    for e in graph["edges"]:
        if e["kind"] == "link":
            near.setdefault(e["from"], set()).add(e["to"])
            near.setdefault(e["to"], set()).add(e["from"])
    distance, ring = {p: 0 for p in found}, list(found)
    for d in range(1, depth + 1):
        ring = sorted({q for p in ring for q in near.get(p, ()) if q not in distance})
        distance.update({q: d for q in ring})
    cover = {e["to"]: e["from"] for e in graph["edges"] if e["kind"] == "covers"}
    context = {cover[p] for p in distance if p in cover} - set(distance)
    keep = set(distance) | context
    out = []
    for p in sorted(keep):
        n = dict(nodes[p])
        if p in found and isinstance(found[p], tuple):
            n["hit"], n["matches"] = found[p]
        elif p in found:
            n["hit"] = found[p]
        elif p in distance:
            n["distance"] = distance[p]
        else:
            n["context"] = True
        out.append(n)
    return {
        "title": "%s: %s" % (graph["title"], query),
        "filter": {"query": query, "words": words, "topics": named, "depth": depth, "step": step},
        "nodes": out,
        "edges": [e for e in graph["edges"] if e["from"] in keep and e["to"] in keep],
    }


def slug(query):
    """The query as a file name: lower case, words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") or "search"
