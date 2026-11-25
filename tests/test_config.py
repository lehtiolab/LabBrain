"""The wiki's own config: labbrain.yaml and topics.yaml at the wiki root."""

import pytest

from labbrain.cli import main
from labbrain.okf.config import BadWikiConfig, WikiConfig, wiki_config

CONFIG = """\
graph:
  hidden: [Session Summary]
  file_url: https://git.example.org/lab/wiki/-/blob/main/{path}
"""
TOPICS = """\
cancer:
  synonyms: [tumour, oncology]
  narrower: [neoantigen]
neoantigen:
"""


def test_no_config_files(tmp_path):
    assert wiki_config(str(tmp_path)) == WikiConfig()


def test_the_config(tmp_path):
    (tmp_path / "labbrain.yaml").write_text(CONFIG)
    (tmp_path / "topics.yaml").write_text(TOPICS)
    assert wiki_config(str(tmp_path)) == WikiConfig(
        hidden=("Session Summary",),
        file_url="https://git.example.org/lab/wiki/-/blob/main/{path}",
        topics={
            "cancer": {"synonyms": ["tumour", "oncology"], "narrower": ["neoantigen"]},
            "neoantigen": {"synonyms": [], "narrower": []},
        },
    )


@pytest.mark.parametrize(
    "name, text, where",
    [
        ("labbrain.yaml", "hot: {days: 30}\n", "the top level"),
        ("labbrain.yaml", "graph: {hide: [Note]}\n", "graph"),
        ("labbrain.yaml", "graph: {hidden: Note}\n", "graph.hidden"),
        ("labbrain.yaml", "graph: {file_url: https://example.org}\n", "graph.file_url"),
        ("labbrain.yaml", "graph: [\n", "the file"),
        ("topics.yaml", "- cancer\n", "the top level"),
        ("topics.yaml", "cancer: {broader: [disease]}\n", "cancer"),
        ("topics.yaml", "cancer: {synonyms: tumour}\n", "cancer"),
        ("topics.yaml", "cancer: {narrower: [neoantigen]}\n", "cancer.narrower"),
        ("topics.yaml", "cancer: {status: maybe}\n", "cancer.status"),
    ],
)
def test_what_it_refuses(tmp_path, name, text, where):
    (tmp_path / name).write_text(text)
    with pytest.raises(BadWikiConfig) as e:
        wiki_config(str(tmp_path))
    assert (e.value.path, e.value.where) == (name, where)


def test_a_topics_status(tmp_path):
    """new until a person reviews it, vetoed when a person says no; none once reviewed."""
    (tmp_path / "topics.yaml").write_text("cancer:\nlfq: {status: new}\nweeds: {status: vetoed}\n")
    topics = wiki_config(str(tmp_path)).topics
    assert [t.get("status") for t in topics.values()] == [None, "new", "vetoed"]


def test_a_bad_config_stops_every_command(vault, capsys):
    (vault / "topics.yaml").write_text("cancer: {synonyms: tumour}\n")
    assert main(["stale", "--vault", str(vault)]) == 2
    assert capsys.readouterr().out.startswith("bad wiki config in topics.yaml: cancer: wanted ")
