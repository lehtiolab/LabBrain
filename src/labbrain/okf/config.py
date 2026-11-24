"""The wiki's own rules, the same for everyone who works on it: labbrain.yaml and topics.yaml at
the wiki root, committed with the wiki. A person's own settings are in env/.env (see cli.py)."""

import os
from dataclasses import dataclass, field

import yaml

from .files import CONFIG, TOPICS, read

TOPIC_KEYS = ("synonyms", "narrower")


class BadWikiConfig(Exception):
    """A wiki config file labbrain can't use."""

    def __init__(self, path, where, wanted):
        self.path, self.where, self.wanted = path, where, wanted
        super().__init__("bad wiki config in %s: %s: wanted %s" % (path, where, wanted))


@dataclass(frozen=True)
class WikiConfig:
    """The wiki's rules. Each default is what a wiki without config files gets."""

    hidden: tuple = ()  # note types the graph page starts with hidden
    file_url: str | None = None  # where the graph page's links lead; {path} is the file's path
    topics: dict = field(default_factory=dict)  # topic -> {"synonyms": [...], "narrower": [...]}


def load_yaml(vault, rel):
    if not os.path.isfile(os.path.join(vault, rel)):
        return None
    try:
        return yaml.safe_load(read(vault, rel))
    except yaml.YAMLError as e:
        raise BadWikiConfig(rel, "the file", "valid YAML (%s)" % " ".join(str(e).split())) from e


def words(v):
    return isinstance(v, list) and all(isinstance(s, str) and s.strip() for s in v)


def wiki_config(vault):
    """The config in labbrain.yaml and topics.yaml at the wiki root; defaults for what's absent."""
    cfg = load_yaml(vault, CONFIG) or {}
    if not isinstance(cfg, dict) or set(cfg) - {"graph"}:
        raise BadWikiConfig(CONFIG, "the top level", "only the key graph")
    graph = cfg.get("graph") or {}
    if not isinstance(graph, dict) or set(graph) - {"hidden", "file_url"}:
        raise BadWikiConfig(CONFIG, "graph", "only the keys hidden and file_url")
    hidden = graph.get("hidden") or []
    if not words(hidden):
        raise BadWikiConfig(CONFIG, "graph.hidden", "a list of note types")
    url = graph.get("file_url")
    if url is not None and not (isinstance(url, str) and "{path}" in url):
        raise BadWikiConfig(CONFIG, "graph.file_url", "a URL with {path} in it")
    raw = load_yaml(vault, TOPICS) or {}
    if not isinstance(raw, dict):
        raise BadWikiConfig(TOPICS, "the top level", "one key per topic")
    topics = {}
    for name, t in raw.items():
        t = t or {}
        if not isinstance(t, dict) or set(t) - set(TOPIC_KEYS):
            raise BadWikiConfig(TOPICS, str(name), "only the keys synonyms and narrower")
        if not all(words(t.get(k, [])) for k in TOPIC_KEYS):
            raise BadWikiConfig(TOPICS, str(name), "synonyms and narrower, each a list of words")
        topics[str(name)] = {k: list(t.get(k, [])) for k in TOPIC_KEYS}
    for name, t in topics.items():
        unknown = [n for n in t["narrower"] if n not in topics]
        if unknown:
            where = "%s.narrower" % name
            raise BadWikiConfig(TOPICS, where, "topics of this file, not %s" % ", ".join(unknown))
    return WikiConfig(tuple(hidden), url, topics)
