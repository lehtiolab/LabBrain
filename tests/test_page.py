"""The graph page: one HTML file with the graph in it, nothing loaded from elsewhere."""

import json
import re

from labbrain.okf.page import graph_page

GRAPH = {
    "title": "Lab & co",
    "nodes": [
        {"id": "A.md", "type": "Note", "title": "</script><script>alert(1)</script>"},
        {"id": "B.md", "type": "Folder Summary", "title": "B"},
    ],
    "edges": [{"from": "B.md", "to": "A.md", "kind": "covers"}],
}


def data(page):
    return json.loads(
        re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S)[1]
    )


def test_the_data_reads_back(tmp_path):
    topics = {"a": {"synonyms": ["b"], "narrower": []}}
    start = {"query": "a", "hits": ["A.md"], "depth": 1}
    page = graph_page(GRAPH, "_maps/search/a.html", ("Note",), None, topics, start)
    assert data(page) == {
        "graph": GRAPH,
        "hidden": ["Note"],
        "fileUrl": None,
        "topics": topics,
        "base": "../../",  # from _maps/search/ back to the wiki root
        "start": start,
    }
    assert "<title>Lab &amp; co</title>" in page


def test_no_text_in_the_wiki_can_end_the_script():
    page = graph_page(GRAPH, "_maps/graph.html")
    assert "alert" in page and "<script>alert" not in page
    assert data(page)["base"] == "../"


def test_nothing_is_loaded_from_elsewhere():
    page = graph_page(GRAPH, "_maps/graph.html")
    assert "<script src" not in page and "<link" not in page and "fetch(" not in page
    assert re.findall(r"\w+://[^\s\"']+", page) == [
        "http://www.w3.org/2000/svg"
    ]  # a name, not a fetch


def test_links_can_lead_to_a_server():
    url = "https://git.example.org/wiki/-/blob/main/{path}"
    assert data(graph_page(GRAPH, "_maps/graph.html", file_url=url))["fileUrl"] == url
