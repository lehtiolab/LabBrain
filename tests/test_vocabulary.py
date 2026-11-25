"""The vocabulary grows from the files: topics.yaml is added to, never rewritten."""

from labbrain.cli import main
from labbrain.okf.config import wiki_config

NEW = {"synonyms": [], "narrower": [], "status": "new"}


def give_topics(vault, rel, topics):
    path = vault / rel
    path.write_text(path.read_text().replace("type:", "topics: [%s]\ntype:" % topics, 1))


def run(vault, capsys):
    code = main(["vocabulary", "--vault", str(vault)])
    return code, capsys.readouterr().out.splitlines()


def test_new_topics_are_added_and_nothing_else_changes(vault, capsys):
    vocabulary = "# our own words\ngarden: {synonyms: [beds]}\npreserving:\n"
    (vault / "topics.yaml").write_text(vocabulary)
    give_topics(vault, "Garden/Garden_summary.md", "Beds, Seed Saving")  # a synonym, a new one
    give_topics(vault, "Shelf/Shelf_summary.md", "preserving, 2026, jars")
    code, out = run(vault, capsys)
    assert code == 0
    assert out[:2] == [
        "added to topics.yaml, with status: new (3): 2026, jars, seed-saving",
        "new, for a person to review (3): 2026, jars, seed-saving",
    ]
    text = (vault / "topics.yaml").read_text()
    assert text.startswith(vocabulary)  # the people's part, comments included, as it was
    assert wiki_config(str(vault)).topics == {
        "garden": {"synonyms": ["beds"], "narrower": []},
        "preserving": {"synonyms": [], "narrower": []},
        "2026": NEW,  # quoted, so YAML reads it as a word
        "jars": NEW,
        "seed-saving": NEW,
    }
    code, out = run(vault, capsys)
    assert (code, out[0]) == (0, "topics.yaml names every topic in use")
    assert (vault / "topics.yaml").read_text() == text
    main(["check", "--vault", str(vault)])
    assert "topics.yaml:" not in capsys.readouterr().out


def test_the_first_topics_make_the_file(vault, capsys):
    give_topics(vault, "Shelf/Shelf_summary.md", "jars")
    assert run(vault, capsys)[0] == 0
    text = (vault / "topics.yaml").read_text()
    assert text.startswith("# The wiki's vocabulary.")
    assert text.endswith("\njars:\n  status: new\n")


def test_what_a_person_reviews(vault, capsys):
    """Spellings close to another topic, and vetoed topics still on files."""
    (vault / "topics.yaml").write_text("normalization:\nweeds: {status: vetoed}\n")
    give_topics(vault, "Shelf/Shelf_summary.md", "normalisation, weeds")
    code, out = run(vault, capsys)
    assert code == 0
    assert out == [
        "added to topics.yaml, with status: new (1): normalisation",
        "new, for a person to review (1): normalisation",
        "spelled like another topic, to merge or keep (1):",
        "  normalisation — normalization",
        "vetoed, still on 1 file(s), to choose others for (run: topics): weeds",
        "  Shelf/Shelf_summary.md",
    ]


def test_a_file_it_cant_add_to(vault, capsys):
    (vault / "topics.yaml").write_text("{garden: {synonyms: [beds]}}\n")
    give_topics(vault, "Shelf/Shelf_summary.md", "jars")
    code, out = run(vault, capsys)
    assert code == 2
    assert out[0].startswith("bad wiki config in topics.yaml: the file: wanted one topic per line")
    assert (vault / "topics.yaml").read_text() == "{garden: {synonyms: [beds]}}\n"
