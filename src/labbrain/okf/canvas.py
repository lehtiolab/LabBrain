"""Pictures of JSON and YAML data: a tree of boxes, as an Obsidian canvas or an HTML page."""

import html
import json
import os
import textwrap

import yaml

from .files import MAPS, join, read, write
from .links import href

DATA_EXT = (".json", ".yaml", ".yml")
# Keys that shape the picture instead of being shown as `key: value` (docs/usage.md).
TITLE, DESCRIPTION, PATH, CHILDREN, LINKS = "title", "description", "path", "children", "links"

# Layout, in pixels. A box's height is guessed from its lines, wrapped at WRAP characters.
WIDTH, GAP_X, GAP_Y = 400, 120, 40
LINE, PAD, WRAP = 24, 40, 44
LINK_COLOR = "6"  # a canvas preset colour: links stand out from the tree's own arrows


class NotData(Exception):
    """A file labbrain can't draw: not JSON or YAML, or not valid as either."""

    def __init__(self, path, why):
        self.path, self.why = path, why
        super().__init__("can't draw %s: %s" % (path, why))


def load(vault, rel):
    """The data in a .json, .yaml or .yml file of the wiki. YAML goes through safe_load only."""
    ext = os.path.splitext(rel)[1].lower()
    if ext not in DATA_EXT:
        raise NotData(rel, "not a .json, .yaml or .yml file")
    if not os.path.isfile(os.path.join(vault, rel)):
        raise NotData(rel, "no such file")
    try:
        text = read(vault, rel)
        return json.loads(text) if ext == ".json" else yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as e:
        raise NotData(rel, " ".join(str(e).split())) from e


def wiki_file(vault, p):
    """p, normalised, if it names a file inside the wiki; else None."""
    if not isinstance(p, str) or not p or os.path.isabs(p):
        return None
    p = os.path.normpath(p)
    if p == os.pardir or p.startswith(os.pardir + os.sep):
        return None
    return p if os.path.isfile(os.path.join(vault, p)) else None


def show(v):
    return json.dumps(v) if v is None or isinstance(v, bool) else str(v)


def boxes(vault, data, title):
    """data as a tree of boxes. A mapping or a list is a box, titled by its key (a list item has
    none); a value that is neither is a line in its parent's box."""
    box = {"title": title, "lines": [], "file": None, "links": [], "kids": []}
    nested = (dict, list)
    if isinstance(data, dict):
        for k, v in data.items():
            k = str(k)
            if k == TITLE and not isinstance(v, nested):
                box["title"] = show(v)
            elif k == DESCRIPTION and not isinstance(v, nested):
                box["lines"].append(show(v))
            elif k == PATH and wiki_file(vault, v):
                box["file"] = wiki_file(vault, v)
            elif k == CHILDREN and isinstance(v, list):
                box["kids"] += [boxes(vault, c, None) for c in v]
            elif k == LINKS and isinstance(v, list):
                for target in v:
                    if wiki_file(vault, target):
                        box["links"].append(wiki_file(vault, target))
                    else:
                        box["lines"].append("links: %s" % show(target))
            elif isinstance(v, nested):
                box["kids"].append(boxes(vault, v, k))
            else:
                box["lines"].append("%s: %s" % (k, show(v)))
    elif isinstance(data, list):
        for v in data:
            if isinstance(v, nested):
                box["kids"].append(boxes(vault, v, None))
            else:
                box["lines"].append("- " + show(v))
    else:
        box["lines"].append(show(data))
    if box["file"] and not box["title"]:
        box["title"] = os.path.basename(box["file"])
    return box


def height(box):
    wrapped = sum(len(textwrap.wrap(t, WRAP)) or 1 for t in box["lines"])
    return PAD + LINE * (wrapped + bool(box["title"]))


def place(box, depth, top):
    """Set x, y and h for box and the boxes under it, left to right; returns the height used."""
    box["h"], box["x"] = height(box), depth * (WIDTH + GAP_X)
    y = top
    for k in box["kids"]:
        y += place(k, depth + 1, y) + GAP_Y
    span = max(box["h"], y - top - GAP_Y)
    box["y"] = top + (span - box["h"]) // 2
    return span


def sides(a, z, kind):
    """The sides of boxes a and z that an arrow between them leaves and enters. The tree runs left
    to right; a link leaves from the side facing its target."""
    if kind == "link" and z["y"] >= a["y"] + a["h"]:
        return "bottom", "top"
    if kind == "link" and z["y"] + z["h"] <= a["y"]:
        return "top", "bottom"
    return ("left", "right") if z["x"] < a["x"] else ("right", "left")


def layout(root):
    """Every box, placed, and the arrows between them as (from, to, kind, from side, to side).

    A link to a wiki file that no box shows gets a box of its own, in a row below the tree.
    """
    tall = place(root, 0, 0)
    placed, stack = [], [root]
    while stack:
        b = stack.pop()
        b["id"] = "n%d" % len(placed)
        placed.append(b)
        stack.extend(reversed(b["kids"]))
    by_file = {b["file"]: b for b in placed if b["file"]}
    loose = dict.fromkeys(p for b in placed for p in b["links"] if p not in by_file)
    for n, p in enumerate(loose):
        b = {"title": os.path.basename(p), "lines": [], "file": p, "links": [], "kids": []}
        b.update(id="n%d" % len(placed), x=n * (WIDTH + GAP_X), y=tall + 3 * GAP_Y, h=height(b))
        placed.append(b)
        by_file[p] = b
    pairs = [(b, k, "tree") for b in placed for k in b["kids"]]
    pairs += [
        (b, by_file[p], "link")
        for b in placed
        for p in dict.fromkeys(b["links"])
        if by_file[p] is not b
    ]
    return placed, [(a["id"], z["id"], kind, *sides(a, z, kind)) for a, z, kind in pairs]


def to_canvas(placed, arrows, title, out):
    """JSON Canvas 1.0, which Obsidian opens. A box's title links to its file, if it has one: a
    click opens it, and hovering shows it."""
    nodes = []
    for b in placed:
        name = "[[%s|%s]]" % (b["file"], b["title"]) if b["file"] else b["title"]
        text = "\n\n".join((["**%s**" % name] if name else []) + ["\n".join(b["lines"])])
        node = {"id": b["id"], "type": "text", "text": text, "x": b["x"], "y": b["y"]}
        nodes.append(dict(node, width=WIDTH, height=b["h"]))
    edges = []
    for i, (a, z, kind, start, end) in enumerate(arrows):
        edge = {"id": "e%d" % i, "fromNode": a, "fromSide": start, "toNode": z, "toSide": end}
        edges.append(dict(edge, color=LINK_COLOR) if kind == "link" else edge)
    return json.dumps({"nodes": nodes, "edges": edges}, indent="\t", ensure_ascii=False) + "\n"


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
body { margin: 0; font: 14px/1.4 system-ui, sans-serif; background: #f6f6f4; color: #222; }
.map { position: relative; margin: 24px; }
.box { position: absolute; box-sizing: border-box; overflow: auto; padding: 10px 12px;
       background: #fff; border: 1px solid #bbb; border-radius: 8px; }
.box.file { border-color: #5a7bd8; }
.box p { margin: 6px 0 0; }
svg { position: absolute; left: 0; top: 0; overflow: visible; pointer-events: none; }
.tree { stroke: #999; fill: none; stroke-width: 1.5; }
.link { stroke: #a35bd1; fill: none; stroke-width: 1.5; stroke-dasharray: 6 4; }
</style>
</head>
<body>
<div class="map" style="width:%(w)dpx;height:%(h)dpx">
%(boxes)s
<svg width="%(w)d" height="%(h)d">
<defs><marker id="tip" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7"
orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#999"/></marker></defs>
%(arrows)s
</svg>
</div>
</body>
</html>
"""


# Where an arrow meets a side, as a fraction of the box's width and height, and which way it points.
SIDE = {
    "right": (1, 0.5, 1, 0),
    "left": (0, 0.5, -1, 0),
    "top": (0.5, 0, 0, -1),
    "bottom": (0.5, 1, 0, 1),
}


def to_html(placed, arrows, title, out):
    """One page, with nothing loaded from elsewhere; a title links to its file, if it has one."""
    by_id = {b["id"]: b for b in placed}
    paths = []
    for a, z, kind, start, end in arrows:
        (a, (fa, ga, da, ea)), (z, (fz, gz, dz, ez)) = (
            (by_id[a], SIDE[start]),
            (by_id[z], SIDE[end]),
        )
        x1, y1 = a["x"] + int(fa * WIDTH), a["y"] + int(ga * a["h"])
        x2, y2 = z["x"] + int(fz * WIDTH), z["y"] + int(gz * z["h"])
        bend = max(abs(y2 - y1) if ea else abs(x2 - x1), GAP_X) // 2
        paths.append(
            '<path class="%s" marker-end="url(#tip)" d="M%d,%d C%d,%d %d,%d %d,%d"/>'
            % (kind, x1, y1, x1 + da * bend, y1 + ea * bend, x2 + dz * bend, y2 + ez * bend, x2, y2)
        )
    divs = []
    for b in placed:
        name = html.escape(b["title"] or "")
        if b["file"]:
            name = '<a href="%s">%s</a>' % (
                html.escape(href(b["file"], os.path.dirname(out))),
                name,
            )
        lines = "".join("<p>%s</p>" % html.escape(t) for t in b["lines"])
        divs.append(
            '<div class="box%s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><b>%s</b>%s</div>'
            % (" file" if b["file"] else "", b["x"], b["y"], WIDTH, b["h"], name, lines)
        )
    return PAGE % {
        "title": html.escape(title),
        "w": max(b["x"] for b in placed) + WIDTH,
        "h": max(b["y"] + b["h"] for b in placed),
        "arrows": "\n".join(paths),
        "boxes": "\n".join(divs),
    }


VIEWS = {"canvas": to_canvas, "html": to_html}


def picture_path(rel, view):
    """Where the picture of wiki file rel goes: the same path under _maps/, with the view's
    extension. A file already in _maps/ gets its picture beside it."""
    parts = rel.split(os.sep)
    stem = os.path.splitext(join(*parts[1:] if parts[0] == MAPS else parts))[0]
    # ponytail: plan.json and plan.yaml in one folder share a picture; keep the extension if that
    # ever bites.
    return join(MAPS, "%s.%s" % (stem, view))


def save(vault, rel, text):
    """Write a file under _maps/, which tells git to ignore it, and everything in it."""
    os.makedirs(os.path.join(vault, os.path.dirname(rel)), exist_ok=True)
    if not os.path.exists(os.path.join(vault, MAPS, ".gitignore")):
        write(
            vault,
            join(MAPS, ".gitignore"),
            "# Pictures drawn by labbrain, never part of the wiki.\n*\n",
        )
    write(vault, rel, text)
    return rel


def picture(vault, data, title, view, out):
    """data drawn in the view ("canvas" or "html"), for saving at out."""
    render = VIEWS[view]
    placed, arrows = layout(boxes(vault, data, title))
    return render(placed, arrows, title, out)


def draw(vault, rels, view):
    """Draw JSON or YAML files of the wiki into _maps/, every file read before any is written.
    Returns the pictures' paths."""
    data = [load(vault, r) for r in rels]
    outs = [picture_path(r, view) for r in rels]
    return [
        save(vault, out, picture(vault, d, os.path.basename(r), view, out))
        for r, d, out in zip(rels, data, outs)
    ]
