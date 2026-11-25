"""The graph agent's work list, from the graph: files that may have topics and have none, files
with vetoed topics, files no link reaches and the links code proposes. Code only: a model then
reads just these."""

from collections import Counter

from .notes import AGENT_TYPES
from .summaries import SUMMARY_TYPE


def curate(graph, topics):
    """What the graph agent should look at.

    summaries, others: summaries, then other agent-written files and raw notes whose author allows
    agent metadata, with no topics yet. vetoed: files with a topic vetoed in the vocabulary.
    unlinked: files other than summaries that no link reaches, in or out; for their authors.
    proposed: the links code proposes, as (from, to, the topics both have); for their authors.
    review: the new topics, for a person to review. unused: topics no file has, vetoed ones aside.
    tags: the tags in use, most first, as (tag, files).
    """
    nodes = graph["nodes"]
    vetoed = {t for t, v in topics.items() if v.get("status") == "vetoed"}
    topics_of = {n["id"]: set(n.get("topics", [])) for n in nodes}
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
        "vetoed": [n for n in nodes if vetoed & set(n.get("topics", []))],
        "unlinked": [n for n in nodes if n["id"] not in linked and n.get("type") != SUMMARY_TYPE],
        "proposed": [
            (e["from"], e["to"], sorted(topics_of[e["from"]] & topics_of[e["to"]]))
            for e in graph["edges"]
            if e["kind"] == "proposed"
        ],
        "review": [t for t, v in topics.items() if v.get("status") == "new"],
        "unused": [t for t in topics if t not in used and t not in vetoed],
        "tags": Counter(t for n in nodes for t in n.get("tags", [])).most_common(),
    }
