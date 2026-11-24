"""Pictures of JSON and YAML files: what goes in the boxes, the layout, what is refused."""

import json
import subprocess
from itertools import combinations

import pytest
import yaml
from conftest import ENV

from labbrain.cli import main
from labbrain.okf.canvas import NotData, boxes, draw, load, picture_path

PLAN = """\
title: Garden plan
description: What goes where.
beds:
  - title: North bed
    path: Garden/Tomatoes.md
    crops: [tomatoes, basil]
  - title: South bed
    links: [Garden/Garden_summary.md, Garden/Beans.md, Garden/Beans.md, Nowhere.md]
budget: 120
"""


@pytest.fixture
def plan(vault):
    (vault / "Garden" / "plan.yaml").write_text(PLAN)
    return "Garden/plan.yaml"


def test_what_goes_in_the_boxes(vault):
    root = boxes(str(vault), yaml.safe_load(PLAN), "plan.yaml")
    assert (root["title"], root["lines"]) == ("Garden plan", ["What goes where.", "budget: 120"])
    beds = root["kids"][0]
    north, south = beds["kids"]
    assert beds["title"] == "beds" and beds["lines"] == []
    assert (north["title"], north["file"]) == ("North bed", "Garden/Tomatoes.md")
    assert north["kids"][0]["lines"] == ["- tomatoes", "- basil"]
    # a link shows its file's title, else its name, once; one that isn't a wiki file is text
    assert south["links"] == [
        ("Garden/Garden_summary.md", "Garden — Summary"),
        ("Garden/Beans.md", "Beans"),
    ]
    assert south["lines"] == ["links: Nowhere.md"]


def test_a_path_outside_the_wiki_is_only_text(vault):
    root = boxes(str(vault), {"path": "../vault/Garden/Beans.md"}, "x")
    assert root["file"] is None and root["lines"] == ["path: ../vault/Garden/Beans.md"]


def overlap(a, b):
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def test_the_canvas(vault, plan):
    assert draw(str(vault), [plan], "canvas") == ["_maps/Garden/plan.canvas"]
    c = json.loads((vault / "_maps" / "Garden" / "plan.canvas").read_text())
    ids = {n["id"] for n in c["nodes"]}
    assert all(set(n) == {"id", "type", "text", "x", "y", "width", "height"} for n in c["nodes"])
    assert all({e["fromNode"], e["toNode"]} <= ids for e in c["edges"])
    assert [(a["id"], b["id"]) for a, b in combinations(c["nodes"], 2) if overlap(a, b)] == []
    text = [n["text"] for n in c["nodes"]]
    assert "**[[Garden/Tomatoes.md|North bed]]**" in text
    assert (
        "**South bed**\n\nlinks: Nowhere.md\n"
        "→ [[Garden/Garden_summary.md|Garden — Summary]] · [[Garden/Beans.md|Beans]]"
    ) in text
    assert len(c["nodes"]) == 5 and len(c["edges"]) == 4  # a tree: links are text, not arrows
    assert {(e["fromSide"], e["toSide"]) for e in c["edges"]} == {("right", "left")}


def test_git_ignores_the_pictures(vault, plan):
    draw(str(vault), [plan], "canvas")
    status = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=vault,
        env=ENV,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "Garden/plan.yaml" in status and "_maps" not in status


def test_the_html_page(vault, plan):
    assert draw(str(vault), [plan], "html") == ["_maps/Garden/plan.html"]
    page = (vault / "_maps" / "Garden" / "plan.html").read_text()
    assert page.count('<div class="box') == 5 and page.count("<path class") == 4
    assert '<a href="../../Garden/Tomatoes.md">North bed</a>' in page
    assert '→ <a href="../../Garden/Garden_summary.md">Garden — Summary</a> · <a' in page
    assert "://" not in page and "<script" not in page  # nothing is loaded from elsewhere


@pytest.mark.parametrize(
    "rel, view, out",
    [
        ("Garden/plan.yaml", "canvas", "_maps/Garden/plan.canvas"),
        ("plan.json", "html", "_maps/plan.html"),
        ("_maps/hierarchy.yaml", "canvas", "_maps/hierarchy.canvas"),  # beside it, not nested
    ],
)
def test_where_a_picture_goes(rel, view, out):
    assert picture_path(rel, view) == out


@pytest.mark.parametrize(
    "rel, text, why",
    [
        ("Garden/Tomatoes.md", None, "not a .json, .yaml or .yml file"),
        ("Nope.yaml", None, "no such file"),
        ("bad.json", "{", "Expecting property name"),
        ("evil.yaml", "!!python/object/apply:os.system ['echo hi']\n", "python/object"),
    ],
)
def test_what_it_refuses(vault, rel, text, why):
    if text:
        (vault / rel).write_text(text)
    with pytest.raises(NotData, match=why):
        load(str(vault), rel)


def test_every_file_is_read_before_any_is_drawn(vault, plan, monkeypatch, capsys):
    monkeypatch.chdir(vault)  # file arguments are relative to where you run labbrain
    assert main(["canvas", "--vault", str(vault), plan, "Nope.yaml"]) == 2
    assert capsys.readouterr().out == "can't draw Nope.yaml: no such file\n"
    assert not (vault / "_maps").exists()


def test_the_command(vault, plan, monkeypatch, capsys):
    monkeypatch.chdir(vault)
    assert main(["canvas", "--vault", str(vault)]) == 2  # no FILE: usage
    assert main(["canvas", "--vault", str(vault), plan]) == 0
    monkeypatch.setenv("LABBRAIN_VIEW", "html")
    assert main(["canvas", "--vault", str(vault), plan]) == 0
    assert main(["canvas", "--view", "canvas", "--vault", str(vault), plan]) == 0
    usage, *drew = capsys.readouterr().out.splitlines()
    assert usage.startswith("usage: canvas FILE...")
    assert drew == ["drew _maps/Garden/%s" % f for f in ("plan.canvas", "plan.html", "plan.canvas")]
