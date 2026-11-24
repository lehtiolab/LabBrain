"""The folder summaries as one tree: children, links, and the picture drawn from it."""

import json

import yaml

from labbrain.cli import main
from labbrain.okf.hierarchy import hierarchy

GARDEN = "Trials of tomatoes and beans in the test garden, with soil notes."
SOIL = {
    "title": "Soil — Summary",
    "path": "Garden/Soil/Soil_summary.md",
    "description": "Compost notes for the garden beds.",
}
SHELF = {
    "title": "Shelf — Summary",
    "path": "Shelf/Shelf_summary.md",
    "description": "Jars kept on the shelf.",
}


def test_the_tree(vault):
    """Soil sits under Garden. Shelf is a git repo of its own, so its summary has no parent.
    Garden's links to its own notes (Tomatoes, Seeds/Pumpkin) and to its child (Soil) are left
    out; Recipes has no summary, so the link goes to the note itself."""
    assert hierarchy(str(vault)) == {
        "title": "vault",
        "path": "index.md",
        "children": [
            {
                "title": "Garden — Summary",
                "path": "Garden/Garden_summary.md",
                "description": GARDEN,
                "links": ["Kitchen/Recipes.md"],
                "children": [SOIL],
            },
            SHELF,
        ],
    }


def summary(title, body):
    return '---\ntype: Folder Summary\ntitle: "%s"\n---\n# %s\n\n%s\n' % (title, title, body)


def test_a_link_to_a_note_goes_to_its_summary(vault):
    """Kitchen gets a summary: Garden's link to Recipes now goes to it, and Kitchen's links to
    Garden's notes become one link to Garden's summary. A link to a parent, a broken link, a link
    inside code and a web link make no arrow."""
    (vault / "Kitchen" / "Kitchen_summary.md").write_text(
        summary(
            "Kitchen — Summary",
            "- [Tomatoes](../Garden/Tomatoes.md#Yields) and [beans](../Garden/Beans.md)\n"
            "- [Pickling](Pickling.md), [gone](Gone.md), `[code](../Shelf/Jars.md)`, "
            "[web](https://example.org)",
        )
    )
    (vault / "Garden" / "Soil" / "Soil_summary.md").write_text(
        summary("Soil — Summary", "- Part of [the garden](../Garden_summary.md)")
    )
    tree = hierarchy(str(vault))
    garden, kitchen, shelf = tree["children"]
    assert garden["links"] == ["Kitchen/Kitchen_summary.md"]
    assert garden["children"] == [
        {"title": "Soil — Summary", "path": "Garden/Soil/Soil_summary.md"}
    ]
    assert kitchen == {
        "title": "Kitchen — Summary",
        "path": "Kitchen/Kitchen_summary.md",
        "links": ["Garden/Garden_summary.md"],
    }
    assert shelf == SHELF


def test_the_command(vault, monkeypatch, capsys):
    assert main(["hierarchy", "--vault", str(vault)]) == 0
    assert main(["hierarchy", "--view", "html", "--vault", str(vault)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "wrote _maps/hierarchy.yaml",
        "drew _maps/hierarchy.canvas",
        "wrote _maps/hierarchy.yaml",
        "drew _maps/hierarchy.html",
    ]
    maps = vault / "_maps"
    assert yaml.safe_load((maps / "hierarchy.yaml").read_text()) == hierarchy(str(vault))
    canvas = json.loads((maps / "hierarchy.canvas").read_text())
    titles = [n["text"].split("\n")[0] for n in canvas["nodes"]]
    assert titles == [
        "**[[index.md|vault]]**",
        "**[[Garden/Garden_summary.md|Garden — Summary]]**",
        "**[[Garden/Soil/Soil_summary.md|Soil — Summary]]**",
        "**[[Shelf/Shelf_summary.md|Shelf — Summary]]**",
    ]
    assert canvas["nodes"][1]["text"].endswith("\n→ [[Kitchen/Recipes.md|Recipes]]")
    assert '<a href="../Garden/Garden_summary.md">' in (maps / "hierarchy.html").read_text()
