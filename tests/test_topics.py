"""Topics from the vocabulary, written by code: on summaries, agent-written files, and raw notes
whose author allows it."""

import pytest

from labbrain.cli import main
from labbrain.okf.frontmatter import fm_list, split_fm
from labbrain.okf.topics import NoTopicsHere, NotTopics, canonical, set_topics

VOCABULARY = "garden: {synonyms: [beds]}\nvegetables: {synonyms: [veg]}\npreserving:\n"
TOPICS = {
    "garden": {"synonyms": ["beds"], "narrower": []},
    "vegetables": {"synonyms": ["veg"], "narrower": []},
    "preserving": {"synonyms": [], "narrower": []},
}


def header(vault, rel):
    return split_fm((vault / rel).read_text())[0]


def test_a_synonym_names_its_topic():
    assert canonical(["Beds", "veg", "garden"], TOPICS) == ["garden", "vegetables"]
    with pytest.raises(NotTopics) as e:
        canonical(["garden", "compost", "soil"], TOPICS)
    assert e.value.words == ["compost", "soil"]


def test_a_summary_keeps_its_key_order(vault):
    rel = "Garden/Garden_summary.md"
    before = (vault / rel).read_text()
    assert set_topics(str(vault), rel, ["garden", "vegetables"], "agent/test")
    after = (vault / rel).read_text()
    lines = after.splitlines()
    assert lines[lines.index("topics: [garden, vegetables]") - 1].startswith("description: ")
    assert [x for x in after.splitlines() if x not in before.splitlines()] == [
        "topics: [garden, vegetables]"
    ]
    assert not set_topics(str(vault), rel, ["garden", "vegetables"], "agent/test")  # no change


def test_another_agent_written_file(vault):
    rel = "Kitchen/Session_2026-01-05.md"  # a Session Summary
    assert set_topics(str(vault), rel, ["vegetables"], "agent/test")
    fm = header(vault, rel)
    assert fm_list(fm, "topics") == ["vegetables"] and "annotated" not in fm


def test_a_raw_note_needs_its_authors_consent(vault):
    rel = "Garden/Tomatoes.md"
    with pytest.raises(NoTopicsHere, match="annotate: true"):
        set_topics(str(vault), rel, ["vegetables"], "agent/test")
    note = vault / rel
    note.write_text(note.read_text().replace("generated:", "annotate: true\ngenerated:", 1))
    body = split_fm(note.read_text())[1]
    assert set_topics(str(vault), rel, ["vegetables"], "agent/a", at="2026-01-01T00:00:00Z")
    assert set_topics(str(vault), rel, ["garden"], "agent/b", at="2026-01-02T00:00:00Z")
    assert set_topics(
        str(vault), rel, ["garden", "preserving"], "agent/a", at="2026-01-03T00:00:00Z"
    )
    fm, after = split_fm(note.read_text())
    assert after == body  # the note's text is never touched
    assert fm_list(fm, "topics") == ["garden", "preserving"]
    assert fm.splitlines() == [  # the author's lines first, then what agents added
        "type: Note",
        "annotate: true",
        "generated: { by: human:tester }",
        "topics: [garden, preserving]",
        "annotated:",
        "  - { by: agent/a, at: 2026-01-03T00:00:00Z, keys: [topics] }",
        "  - { by: agent/b, at: 2026-01-02T00:00:00Z, keys: [topics] }",
    ]


@pytest.mark.parametrize(
    "rel, why", [("Garden/index.md", "not a note"), ("Garden/Beans.md", "no header")]
)
def test_files_it_refuses(vault, rel, why):
    with pytest.raises(NoTopicsHere, match=why):
        set_topics(str(vault), rel, ["garden"], "agent/test")


def test_the_command(vault, monkeypatch, capsys):
    (vault / "topics.yaml").write_text(VOCABULARY)
    monkeypatch.chdir(vault)
    summary = "Garden/Garden_summary.md"
    before = (vault / summary).read_text()
    assert main(["topics", "--by", "agent/test", summary, "beds", "compost"]) == 2
    assert (vault / summary).read_text() == before  # nothing written
    assert main(["topics", summary, "garden"]) == 2  # no --by
    assert main(["topics", "--by", "ada@example.org", summary, "garden"]) == 2
    assert main(["topics", "--by", "agent/test", summary, "beds", "veg"]) == 0
    assert main(["topics", "--by", "agent/test", summary, "garden", "vegetables"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "not in topics.yaml: compost (nothing was written; propose them to a person)"
    assert out[-2:] == [
        "set topics of %s: garden, vegetables" % summary,
        "unchanged: %s: garden, vegetables" % summary,
    ]


def test_check_flags_a_topic_outside_the_vocabulary(vault, capsys):
    (vault / "topics.yaml").write_text(VOCABULARY)
    shelf = vault / "Shelf" / "Shelf_summary.md"
    shelf.write_text(
        shelf.read_text().replace("type: Folder Summary", "type: Folder Summary\ntopics: [jars]")
    )
    main(["check", "--vault", str(vault)])
    assert "Shelf/Shelf_summary.md: topics not in topics.yaml: jars" in capsys.readouterr().out
