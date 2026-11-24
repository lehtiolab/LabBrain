"""The wiki's graph: its nodes and edges, the cache that spares rereading files, the command."""

import json

from labbrain.cli import main
from labbrain.okf import graph as graph_module
from labbrain.okf.graph import build_graph, load_cache, write_graph


def edges(graph, kind, source=None):
    return sorted(
        (e["from"], e["to"])
        for e in graph["edges"]
        if e["kind"] == kind and source in (None, e["from"])
    )


def test_the_nodes(vault):
    """Every markdown file but index.md and log.md; a title from the header, else the first
    heading, else the file name."""
    graph, _ = build_graph(str(vault), {})
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert graph["title"] == "vault"
    assert sorted(nodes) == [
        "Garden/Beans.md",
        "Garden/Fresh.md",
        "Garden/Garden_summary.md",
        "Garden/Seeds/Pumpkin.md",
        "Garden/Soil/Compost.md",
        "Garden/Soil/Soil_summary.md",
        "Garden/Tomatoes.md",
        "Kitchen/Pickling.md",
        "Kitchen/Recipes.md",
        "Kitchen/Session_2026-01-05.md",
        "Kitchen/Shopping.md",
        "Kitchen/Spice rack.md",
        "Shelf/Jars.md",
        "Shelf/Shelf_summary.md",
    ]
    garden = nodes["Garden/Garden_summary.md"]
    assert (garden["title"], garden["type"]) == ("Garden — Summary", "Folder Summary")
    assert garden["description"].startswith("Trials of tomatoes")
    assert nodes["Garden/Tomatoes.md"]["title"] == "Tomatoes"  # its first heading
    assert len(garden["hash"]) == 40


def test_the_edges(vault):
    """Links resolve the way Obsidian resolves them; links in code, to files that don't exist,
    to non-markdown files and to the file itself make no edge."""
    graph, _ = build_graph(str(vault), {})
    assert edges(graph, "link", "Garden/Tomatoes.md") == [
        ("Garden/Tomatoes.md", "Garden/Beans.md"),  # [[Beans]]
        ("Garden/Tomatoes.md", "Kitchen/Recipes.md"),  # [[Recipes#Salsa|salsa]]
        ("Garden/Tomatoes.md", "Kitchen/Spice rack.md"),  # [[Spice rack]]
    ]
    # [Recipes](Recipes.md) from Garden/: no such file there, so the closest by name
    assert ("Garden/Fresh.md", "Kitchen/Recipes.md") in edges(graph, "link")
    assert edges(graph, "covers", "Garden/Garden_summary.md") == [
        ("Garden/Garden_summary.md", p)
        for p in (
            "Garden/Beans.md",
            "Garden/Fresh.md",
            "Garden/Seeds/Pumpkin.md",
            "Garden/Tomatoes.md",
        )
    ]
    assert edges(graph, "child") == [("Garden/Garden_summary.md", "Garden/Soil/Soil_summary.md")]


def test_the_same_wiki_gives_the_same_bytes(vault):
    write_graph(str(vault))
    first = (vault / "_maps" / "graph.json").read_bytes()
    write_graph(str(vault))
    assert (vault / "_maps" / "graph.json").read_bytes() == first


def test_only_changed_files_are_read(vault, monkeypatch):
    write_graph(str(vault))
    old = load_cache(str(vault))
    (vault / "Garden" / "Beans.md").write_text("# Beans\nNow beside the [[Pumpkin]].\n")
    read = []
    real = graph_module.parse
    monkeypatch.setattr(graph_module, "parse", lambda text: read.append(text) or real(text))
    graph, fresh = write_graph(str(vault))
    assert (fresh, len(read)) == (1, 1)
    assert edges(graph, "link", "Garden/Beans.md") == [
        ("Garden/Beans.md", "Garden/Seeds/Pumpkin.md")
    ]
    new = load_cache(str(vault))
    assert len(new) == len(old) and set(new) != set(old)  # the old version's entry is gone


def test_a_damaged_cache_is_rebuilt(vault):
    (vault / "_maps").mkdir()
    (vault / "_maps" / "graph-cache.json").write_text('{"abc": "not an entry"}')
    assert load_cache(str(vault)) == {}
    _, fresh = write_graph(str(vault))
    assert fresh == 14


def test_the_command(vault, capsys):
    assert main(["graph", "--vault", str(vault)]) == 0
    assert capsys.readouterr().out == (
        "wrote _maps/graph.json: 14 files; 18 link, 6 covers and 1 child edges; "
        "14 file(s) read, the rest unchanged\n"
        "drew _maps/graph.html\n"
    )
    graph = json.loads((vault / "_maps" / "graph.json").read_text())
    assert list(graph) == ["title", "nodes", "edges"]
