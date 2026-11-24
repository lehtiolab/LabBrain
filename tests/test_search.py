"""Search, cheapest first: headers, then full text, then the links around what was found."""

import json

import pytest

from labbrain.cli import main
from labbrain.okf.graph import build_graph
from labbrain.okf.search import meanings, search, slug

TOPICS = {
    "cancer": {"synonyms": ["tumour"], "narrower": ["neoantigen"]},
    "neoantigen": {"synonyms": ["neo-antigen"], "narrower": []},
}


def found(vault, query, topics=None, **kw):
    graph, _ = build_graph(str(vault), {})
    return search(str(vault), graph, query, topics or {}, **kw)


def by_id(result):
    return {n["id"]: n for n in result["nodes"]}


def test_the_vocabulary_widens_a_query():
    assert meanings("Tumour", TOPICS) == (
        ["cancer", "neo-antigen", "neoantigen", "tumour"],
        ["cancer", "neoantigen"],
    )
    assert meanings("neoantigen", TOPICS) == (["neo-antigen", "neoantigen"], ["neoantigen"])
    assert meanings("beans", TOPICS) == (["beans"], [])


def test_step_1_the_headers(vault):
    """Title, description and path, from the start of a word, then links one away."""
    result = found(vault, "tomato")
    nodes = by_id(result)
    assert result["filter"]["step"] == 1
    hits = {p: n["hit"] for p, n in nodes.items() if "hit" in n}
    assert hits == {"Garden/Tomatoes.md": "title", "Garden/Garden_summary.md": "description"}
    assert nodes["Kitchen/Recipes.md"]["distance"] == 1
    assert found(vault, "omato")["nodes"] == []  # not from the middle of a word


def test_step_1_topics_and_tags(vault):
    shelf = vault / "Shelf" / "Shelf_summary.md"
    shelf.write_text(
        shelf.read_text().replace("type: Folder Summary", "type: Folder Summary\ntopics: [storage]")
    )
    topics = {"storage": {"synonyms": ["pantry"], "narrower": []}}
    assert by_id(found(vault, "pantry", topics))["Shelf/Shelf_summary.md"]["hit"] == "topics"


def test_step_2_the_full_text(vault):
    """No header names brine, so the text is searched. Jars is linked to the hit, and the
    Shelf summary covers Jars."""
    result = found(vault, "brine")
    nodes = by_id(result)
    assert result["filter"]["step"] == 2
    assert (nodes["Kitchen/Pickling.md"]["hit"], nodes["Kitchen/Pickling.md"]["matches"]) == (
        "text",
        3,
    )
    assert nodes["Shelf/Jars.md"]["distance"] == 1
    assert nodes["Shelf/Shelf_summary.md"]["context"] is True
    assert {(e["from"], e["to"]) for e in result["edges"]} >= {
        ("Kitchen/Pickling.md", "Shelf/Jars.md"),
        ("Shelf/Shelf_summary.md", "Shelf/Jars.md"),
    }


def test_text_also_searches_when_headers_match(vault):
    result = found(vault, "tomato", text=True)
    assert result["filter"]["step"] == 2
    assert by_id(result)["Kitchen/Recipes.md"]["hit"] == "text"


def test_depth(vault):
    assert {n["id"] for n in found(vault, "brine", depth=0)["nodes"]} == {"Kitchen/Pickling.md"}
    deeper = by_id(found(vault, "brine", depth=2))
    assert deeper["Shelf/Jars.md"]["distance"] == 1
    assert "distance" not in deeper["Kitchen/Pickling.md"]


def test_the_command(vault, capsys):
    assert main(["search", "--vault", str(vault), "Brine"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "looked for: brine",
        "step 2, the full text: 1 file(s)",
        "  Kitchen/Pickling.md — Pickling  (3 matches)",
        "step 3, linked up to 1 away: 1 file(s)",
        "  Shelf/Jars.md — Jars  (1 away)",
        "and the summaries over them: 1 file(s)",
        "  Shelf/Shelf_summary.md — Shelf — Summary",
        "wrote _maps/search/brine.json",
        "drew _maps/search/brine.html",
    ]
    result = json.loads((vault / "_maps" / "search" / "brine.json").read_text())
    assert result["filter"] == {
        "query": "Brine",
        "words": ["brine"],
        "topics": [],
        "depth": 1,
        "step": 2,
    }


@pytest.mark.parametrize("args, code", [(["nothing-like-this"], 1), (["--depth", "-1", "jars"], 2)])
def test_nothing_found_and_usage(vault, args, code):
    assert main(["search", "--vault", str(vault), *args]) == code
    assert not (vault / "_maps" / "search").exists()


def test_slug():
    assert slug("Mass Spectrometry!") == "mass-spectrometry"
    assert slug("***") == "search"
