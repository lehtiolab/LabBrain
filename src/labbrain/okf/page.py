"""The graph page: one HTML file, with the graph inside it, for exploring the wiki in a browser."""

import html
import json
import os
from importlib.resources import files

TEMPLATE = "graph_page.html"


def graph_page(graph, out, hidden=(), file_url=None, topics=None, start=None):
    """The page to save at out (a path in the wiki), with nothing loaded from elsewhere.

    hidden: note types it starts with switched off. file_url: where its links lead, with {path}
    for the file's path; else they are relative to the page. topics: the wiki's vocabulary, for
    searching in the page. start: what `labbrain search` found ({"query", "hits", "depth"}), to
    open on; else it opens at the wiki's root.
    """
    data = {
        "graph": graph,
        "hidden": list(hidden),
        "fileUrl": file_url,
        "topics": topics or {},
        "base": "../" * out.replace(os.sep, "/").count("/"),
        "start": start,
    }
    # "<" escaped, so no text in the wiki can close the script tag it sits in
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    before, after = (
        files(__package__).joinpath(TEMPLATE).read_text(encoding="utf-8").split("__DATA__")
    )
    return before.replace("__TITLE__", html.escape(graph["title"]), 1) + text + after
