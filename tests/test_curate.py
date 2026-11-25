"""The graph agent's work list."""

from labbrain.cli import main
from labbrain.okf.curate import curate
from labbrain.okf.graph import build_graph
from labbrain.okf.index import build_indexes

TOPICS = {
    "garden": {"synonyms": [], "narrower": []},
    "preserving": {"synonyms": [], "narrower": []},
    "soil": {"synonyms": [], "narrower": [], "status": "vetoed"},
    "beans": {"synonyms": [], "narrower": [], "status": "new"},
}


def ids(nodes):
    return [n["id"] for n in nodes]


def test_the_work_list(vault):
    tomatoes = vault / "Garden" / "Tomatoes.md"  # its author allows agent metadata
    tomatoes.write_text(tomatoes.read_text().replace("generated:", "annotate: true\ngenerated:", 1))
    soil = vault / "Garden" / "Soil" / "Soil_summary.md"
    soil.write_text(
        soil.read_text().replace(
            "type: Folder Summary", "type: Folder Summary\ntopics: [garden, soil]"
        )
    )
    shopping = vault / "Kitchen" / "Shopping.md"  # ingested now, and still linked from nowhere
    shopping.write_text("---\ntype: Note\n---\n" + shopping.read_text())
    build_indexes(str(vault))
    graph, _ = build_graph(str(vault), {}, set(), {})
    work = curate(graph, TOPICS)
    assert ids(work["summaries"]) == ["Garden/Garden_summary.md", "Shelf/Shelf_summary.md"]
    assert ids(work["others"]) == [  # a Method, a Session Summary and a note with consent
        "Garden/Tomatoes.md",
        "Kitchen/Pickling.md",
        "Kitchen/Session_2026-01-05.md",
    ]
    assert ids(work["vetoed"]) == ["Garden/Soil/Soil_summary.md"]  # soil is vetoed
    assert ids(work["unlinked"]) == ["Kitchen/Shopping.md"]
    assert work["unused"] == ["preserving", "beans"]  # and soil, which is vetoed
    assert work["review"] == ["beans"]
    assert work["proposed"] == []


def test_proposed_links_are_for_their_authors(vault):
    for rel in ("Kitchen/Spice rack.md", "Shelf/Jars.md"):
        path = vault / rel
        path.write_text(path.read_text().replace("type:", "topics: [garden, preserving]\ntype:", 1))
    graph, _ = build_graph(str(vault), {}, set(), {})
    assert curate(graph, TOPICS)["proposed"] == [
        ("Kitchen/Spice rack.md", "Shelf/Jars.md", ["garden", "preserving"])
    ]


def test_the_command(vault, capsys):
    assert main(["curate", "--vault", str(vault)]) == 1  # no vocabulary yet: every topic is new
    assert capsys.readouterr().out.startswith("no topics.yaml yet: every topic set now is new")
    (vault / "topics.yaml").write_text("garden:\n")
    assert main(["curate", "--vault", str(vault)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[:3] == [
        "summaries without topics (3):",
        "  Garden/Garden_summary.md — Garden — Summary",
        "      Trials of tomatoes and beans in the test garden, with soil notes.",
    ]
    assert out[-1] == "work for the graph agent"
    for s in (
        "Garden/Garden_summary.md",
        "Garden/Soil/Soil_summary.md",
        "Shelf/Shelf_summary.md",
        "Kitchen/Pickling.md",
        "Kitchen/Session_2026-01-05.md",
    ):
        assert (
            main(["topics", "--by", "agent/test", "--vault", str(vault), str(vault / s), "garden"])
            == 0
        )
    capsys.readouterr()
    assert main(["curate", "--vault", str(vault)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "nothing for the graph agent to do"
