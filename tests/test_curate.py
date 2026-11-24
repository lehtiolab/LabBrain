"""The graph agent's work list."""

from labbrain.cli import main
from labbrain.okf.curate import curate
from labbrain.okf.graph import build_graph

TOPICS = {
    "garden": {"synonyms": [], "narrower": []},
    "preserving": {"synonyms": [], "narrower": []},
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
    graph, _ = build_graph(str(vault), {})
    work = curate(graph, TOPICS)
    assert ids(work["summaries"]) == ["Garden/Garden_summary.md", "Shelf/Shelf_summary.md"]
    assert ids(work["others"]) == [  # a Method, a Session Summary and a note with consent
        "Garden/Tomatoes.md",
        "Kitchen/Pickling.md",
        "Kitchen/Session_2026-01-05.md",
    ]
    assert ids(work["unknown"]) == ["Garden/Soil/Soil_summary.md"]  # soil isn't in the vocabulary
    assert ids(work["unlinked"]) == ["Kitchen/Shopping.md"]
    assert work["unused"] == ["preserving"]


def test_the_command(vault, capsys):
    assert main(["curate", "--vault", str(vault)]) == 0  # no vocabulary: nothing an agent can set
    assert capsys.readouterr().out.startswith("no vocabulary yet: topics.yaml")
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
