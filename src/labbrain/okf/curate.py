"""The graph agent's work list, from the graph: files that may have topics and have none, topics
outside the vocabulary, and files no link reaches. Code only: a model then reads just these."""

from collections import Counter

from .notes import AGENT_TYPES
from .summaries import SUMMARY_TYPE


def curate(graph, topics):
    """What the graph agent should look at.

    summaries, others: summaries, then other agent-written files and raw notes whose author allows
    agent metadata, with no topics yet. unknown: files with topics not in the vocabulary.
    unlinked: files other than summaries that no link reaches, in or out; for their authors.
    unused: topics no file has. tags: the tags in use, most first, as (tag, files).
    """
    nodes = graph["nodes"]
    linked = {e[k] for e in graph["edges"] if e["kind"] == "link" for k in ("from", "to")}
    bare = [
        n
        for n in nodes
        if (n.get("type") in AGENT_TYPES or n.get("annotate")) and not n.get("topics")
    ]
    used = {t for n in nodes for t in n.get("topics", [])}
    return {
        "summaries": [n for n in bare if n.get("type") == SUMMARY_TYPE],
        "others": [n for n in bare if n.get("type") != SUMMARY_TYPE],
        "unknown": [n for n in nodes if any(t not in topics for t in n.get("topics", []))],
        "unlinked": [n for n in nodes if n["id"] not in linked and n.get("type") != SUMMARY_TYPE],
        "unused": [t for t in topics if t not in used],
        "tags": Counter(t for n in nodes for t in n.get("tags", [])).most_common(),
    }
