"""The wiki's graph: its nodes and edges, the links it proposes, the cache that spares rereading
files, the command."""

import json

from labbrain.cli import main
from labbrain.okf import graph as graph_module
from labbrain.okf.graph import build_graph, load_cache, write_graph
from labbrain.okf.index import build_indexes

HEADER = "---\ntype: Note\n---\n"


def edges(graph, kind, source=None):
    return sorted(
        (e["from"], e["to"])
        for e in graph["edges"]
        if e["kind"] == kind and source in (None, e["from"])
    )


def test_the_nodes(vault):
    """Every ingested markdown file but index.md and log.md; a title from the header, else the
    first heading, else the file name."""
    graph, _ = build_graph(str(vault), {}, set(), {})
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert graph["title"] == "vault"
    assert sorted(nodes) == [
        "Garden/Garden_summary.md",
        "Garden/Seeds/Pumpkin.md",
        "Garden/Soil/Compost.md",
        "Garden/Soil/Soil_summary.md",
        "Garden/Tomatoes.md",
        "Kitchen/Pickling.md",
        "Kitchen/Recipes.md",
        "Kitchen/Session_2026-01-05.md",
        "Kitchen/Spice rack.md",
        "Shelf/Jars.md",
        "Shelf/Shelf_summary.md",
    ]
    garden = nodes["Garden/Garden_summary.md"]
    assert (garden["title"], garden["type"]) == ("Garden — Summary", "Folder Summary")
    assert garden["description"].startswith("Trials of tomatoes")
    assert nodes["Garden/Tomatoes.md"]["title"] == "Tomatoes"  # its first heading
    assert "annotate" not in nodes["Garden/Tomatoes.md"]  # only where the author said true
    assert len(garden["hash"]) == 40


def test_only_ingested_files_are_nodes(vault):
    """A header with a type, and a listing in the index.md of the file's own folder. The others
    wait, and no edge leads to them."""
    graph, _ = build_graph(str(vault), {}, set(), {})
    # Beans and Shopping have no header; Fresh has none and came after the last `index`
    assert graph["waiting"] == ["Garden/Beans.md", "Garden/Fresh.md", "Kitchen/Shopping.md"]
    assert not [e for e in graph["edges"] if set(graph["waiting"]) & {e["from"], e["to"]}]
    fresh = vault / "Garden" / "Fresh.md"
    fresh.write_text(HEADER + fresh.read_text())
    late = vault / "Kitchen" / "Late.md"  # a header, but no index.md lists it yet
    late.write_text(HEADER + "# Late\n")
    garden = vault / "Garden" / "index.md"  # a link from another folder's index.md lists nothing
    garden.write_text(garden.read_text() + "\n* [Late](../Kitchen/Late.md)\n")
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert graph["waiting"] == [
        "Garden/Beans.md",
        "Garden/Fresh.md",
        "Kitchen/Late.md",
        "Kitchen/Shopping.md",
    ]
    build_indexes(str(vault))
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert graph["waiting"] == ["Garden/Beans.md", "Kitchen/Shopping.md"]


def test_the_edges(vault):
    """Links resolve the way Obsidian resolves them; links in code, to files that don't exist,
    to non-markdown files and to the file itself make no edge."""
    fresh = vault / "Garden" / "Fresh.md"
    fresh.write_text(HEADER + fresh.read_text())
    build_indexes(str(vault))
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert edges(graph, "link", "Garden/Tomatoes.md") == [
        ("Garden/Tomatoes.md", "Kitchen/Recipes.md"),  # [[Recipes#Salsa|salsa]]
        ("Garden/Tomatoes.md", "Kitchen/Spice rack.md"),  # [[Spice rack]]
    ]  # and [[Beans]], which isn't ingested
    # [Recipes](Recipes.md) from Garden/: no such file there, so the closest by name
    assert ("Garden/Fresh.md", "Kitchen/Recipes.md") in edges(graph, "link")
    assert edges(graph, "covers", "Garden/Garden_summary.md") == [
        ("Garden/Garden_summary.md", p)
        for p in ("Garden/Fresh.md", "Garden/Seeds/Pumpkin.md", "Garden/Tomatoes.md")
    ]
    assert edges(graph, "child") == [("Garden/Garden_summary.md", "Garden/Soil/Soil_summary.md")]


def test_the_same_wiki_gives_the_same_bytes(vault):
    write_graph(str(vault), set(), {})
    first = (vault / "_maps" / "graph.json").read_bytes()
    write_graph(str(vault), set(), {})
    assert (vault / "_maps" / "graph.json").read_bytes() == first


def test_only_changed_files_are_read(vault, monkeypatch):
    write_graph(str(vault), set(), {})
    old = load_cache(str(vault))
    (vault / "Garden" / "Beans.md").write_text(HEADER + "# Beans\nNow beside the [[Pumpkin]].\n")
    read = []
    real = graph_module.parse
    monkeypatch.setattr(graph_module, "parse", lambda text: read.append(text) or real(text))
    graph, fresh = write_graph(str(vault), set(), {})
    assert (fresh, len(read)) == (1, 1)
    assert edges(graph, "link", "Garden/Beans.md") == [
        ("Garden/Beans.md", "Garden/Seeds/Pumpkin.md")
    ]
    new = load_cache(str(vault))
    assert len(new) == len(old) and set(new) != set(old)  # the old version's entry is gone


def test_an_old_cache_is_rebuilt(vault):
    """A cache from another version of parse() would miss fields: it is read again."""
    write_graph(str(vault), set(), {})
    cache = vault / "_maps" / "graph-cache.json"
    cache.write_text(json.dumps(json.loads(cache.read_text())["files"]))  # the version-1 shape
    assert load_cache(str(vault)) == {}
    assert write_graph(str(vault), set(), {})[1] == 20  # 14 notes and 6 index.md


def test_consent_is_in_the_graph(vault):
    note = vault / "Garden" / "Tomatoes.md"
    note.write_text(note.read_text().replace("generated:", "annotate: true\ngenerated:", 1))
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert next(n for n in graph["nodes"] if n["id"] == "Garden/Tomatoes.md")["annotate"] is True


def test_a_damaged_cache_is_rebuilt(vault):
    (vault / "_maps").mkdir()
    (vault / "_maps" / "graph-cache.json").write_text('{"abc": "not an entry"}')
    assert load_cache(str(vault)) == {}
    _, fresh = write_graph(str(vault), set(), {})
    assert fresh == 20


def give_topics(vault, rel, topics):
    path = vault / rel
    path.write_text(path.read_text().replace("type:", "topics: [%s]\ntype:" % topics, 1))


def test_proposed_links(vault):
    """Files that share two topics, with no edge between them and neither in the other's folder."""
    for rel, topics in (
        ("Kitchen/Spice rack.md", "garden, preserving"),
        ("Shelf/Jars.md", "garden, preserving"),  # neither links the other: proposed
        ("Garden/Tomatoes.md", "red, sauce, soil, worms"),
        ("Kitchen/Recipes.md", "red, sauce"),  # the tomatoes link it already
        ("Garden/Soil/Compost.md", "soil, worms"),  # under the tomatoes' folder: the tree has it
        ("Kitchen/Pickling.md", "brine, jars"),
        ("Kitchen/Session_2026-01-05.md", "brine, jars"),  # in the same folder
        ("Shelf/Shelf_summary.md", "garden"),  # one topic in common only
    ):
        give_topics(vault, rel, topics)
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert edges(graph, "proposed") == [("Kitchen/Spice rack.md", "Shelf/Jars.md")]
    graph, _ = build_graph(str(vault), {}, {("Kitchen/Spice rack.md", "Shelf/Jars.md")}, {})
    assert edges(graph, "proposed") == []


def test_topics_as_the_vocabulary_names_them(vault):
    """A topic merged into another as its synonym is that topic: no file needs rewriting."""
    give_topics(vault, "Kitchen/Spice rack.md", "LFQ, Garden")
    give_topics(vault, "Shelf/Jars.md", "label-free, garden")
    topics = {
        "label-free": {"synonyms": ["lfq"], "narrower": []},
        "garden": {"synonyms": [], "narrower": []},
    }
    graph, _ = build_graph(str(vault), {}, set(), topics)
    assert next(n for n in graph["nodes"] if n["id"] == "Kitchen/Spice rack.md")["topics"] == [
        "label-free",
        "garden",
    ]
    assert edges(graph, "proposed") == [("Kitchen/Spice rack.md", "Shelf/Jars.md")]
    topics["garden"]["status"] = "vetoed"  # one topic in common left: no longer proposed
    assert edges(build_graph(str(vault), {}, set(), topics)[0], "proposed") == []


def test_rejecting_a_proposed_link(vault, capsys):
    for rel in ("Kitchen/Spice rack.md", "Shelf/Jars.md"):
        give_topics(vault, rel, "garden, preserving")
    pair = [str(vault / "Shelf" / "Jars.md"), str(vault / "Kitchen" / "Spice rack.md")]
    run = ["reject", "--vault", str(vault)]
    assert main(run + ["--by", "agent/test"] + pair) == 2  # a person's call, never an agent's
    assert main(run + ["--by", "human:ada", pair[0], str(vault / "Kitchen" / "Recipes.md")]) == 2
    assert "not a link the graph proposes" in capsys.readouterr().out
    assert main(run + ["--by", "human:ada"] + pair) == 0
    record = json.loads((vault / "_maps" / "rejected.jsonl").read_text())
    assert (record["by"], record["rejected"]) == (
        "human:ada",
        ["Kitchen/Spice rack.md", "Shelf/Jars.md"],
    )
    assert main(run + ["--by", "human:ada"] + pair) == 2  # no longer proposed
    graph = json.loads((vault / "_maps" / "graph.json").read_text())
    assert edges(graph, "proposed") == []


def test_a_damaged_rejection_stops_the_graph(vault, capsys):
    (vault / "_maps").mkdir()
    (vault / "_maps" / "rejected.jsonl").write_text('{"rejected": ["only one"]}\n')
    assert main(["graph", "--vault", str(vault)]) == 2
    assert capsys.readouterr().out.startswith("bad record in _maps/rejected.jsonl, line 1:")


def test_the_command(vault, capsys):
    assert main(["graph", "--vault", str(vault)]) == 0
    assert capsys.readouterr().out == (
        "wrote _maps/graph.json: 11 files; 13 link, 4 covers, 1 child and 0 proposed edges; "
        "20 file(s) read, the rest unchanged\n"
        "3 file(s) not ingested yet: no header with a type, or not listed in their folder's "
        "index.md:\n"
        "  Garden/Beans.md\n"
        "  Garden/Fresh.md\n"
        "  Kitchen/Shopping.md\n"
        "drew _maps/graph.html\n"
    )
    graph = json.loads((vault / "_maps" / "graph.json").read_text())
    assert list(graph) == ["title", "nodes", "edges", "waiting"]
