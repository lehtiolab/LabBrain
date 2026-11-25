"""Topics set on a file's header: a summary or another agent-written file, or a raw note whose
author allows agent metadata (`annotate: true`).

The model chooses the topics, from topics.yaml first. This code maps each word to the topic it
names, lets a few new ones through, and writes them, with the `annotated` entry OKF asks for on a
raw note (skills/okf-conventions). `labbrain vocabulary` then adds the new ones to topics.yaml.
"""

import os
import re

from .files import RESERVED, read, write
from .frontmatter import (
    SCALAR,
    fm_blocks,
    fm_get,
    fm_list,
    set_fm_block,
    split_fm,
    unquote_yaml,
    with_fm,
    ys,
)
from .notes import AGENT_TYPES
from .summaries import SUMMARY_TYPE, assemble, now, summary_in

ANNOTATED = re.compile(
    r"^\s*-\s*\{\s*by:\s*%s\s*,\s*at:\s*([^,}\s]+)\s*,\s*keys:\s*\[([^\]]*)\]\s*\}\s*$" % SCALAR
)


MAX_NEW = 3  # new topics a file may bring at once, beyond those in topics.yaml


class NotTopics(Exception):
    """Words labbrain won't write as topics."""

    def __init__(self, words, why):
        self.words, self.why = words, why
        super().__init__("%s: %s (nothing was written)" % (why, ", ".join(words)))


class TooManyNew(Exception):
    """More new topics for one file than MAX_NEW."""

    def __init__(self, words, most):
        self.words, self.most = words, most
        super().__init__(
            "%d new topics, and at most %d may be new: %s (nothing was written; choose from "
            "topics.yaml first)" % (len(words), most, ", ".join(words))
        )


class NoTopicsHere(Exception):
    """A file whose header labbrain won't give topics."""

    def __init__(self, path, why):
        self.path, self.why = path, why
        super().__init__("topics not set on %s: %s" % (path, why))


def as_topic(word):
    """A word as a topic is written: lower case, with hyphens between its parts."""
    return re.sub(r"[\W_]+", "-", word.lower()).strip("-")


def topic_names(topics):
    """{key of a name or a synonym: the topic's name}; a name wins over another topic's synonym."""
    out = {as_topic(n): n for n in topics}
    for n, t in topics.items():
        for w in t["synonyms"]:
            out.setdefault(as_topic(w), n)
    return out


def canonical(words, topics):
    """(names, new): each word as the topic it names, itself or by a synonym, else as a new topic,
    in order and each once; and the new ones. Refuses vetoed topics, words with no letter or
    digit, and more than MAX_NEW new topics."""
    idx = topic_names(topics)
    empty = [w for w in words if not as_topic(w)]
    if empty:
        raise NotTopics(empty, "no letter or digit")
    names = list(dict.fromkeys(idx.get(as_topic(w), as_topic(w)) for w in words))
    vetoed = [n for n in names if topics.get(n, {}).get("status") == "vetoed"]
    if vetoed:
        raise NotTopics(vetoed, "vetoed in topics.yaml")
    new = [n for n in names if n not in topics]
    if len(new) > MAX_NEW:
        raise TooManyNew(new, MAX_NEW)
    return names, new


def entry(by, at, keys):
    return "  - { by: %s, at: %s, keys: [%s] }" % (ys(by), at, ", ".join(keys))


def annotated_lines(fm, by, at, key):
    """The `annotated` block, with by's own entry naming key and dated at; other entries kept."""
    lines, found = ["annotated:"], False
    for k, block in fm_blocks(fm or ""):
        for line in block[1:] if k == "annotated" else []:
            m = ANNOTATED.match(line)
            if m and unquote_yaml(m.group(1)) == by:
                keys = [x.strip() for x in m.group(3).split(",") if x.strip()]
                line, found = entry(by, at, list(dict.fromkeys(keys + [key]))), True
            if line.strip():
                lines.append(line)
    return lines if found else lines + [entry(by, at, [key])]


def set_topics(vault, rel, names, by, at=None):
    """Write topics (from canonical()) into rel's header. True if the file changed.

    A summary keeps its canonical key order. A raw note needs `annotate: true` from its author,
    and gets by's entry in `annotated`; its text is never touched.
    """
    if not rel.endswith(".md") or os.path.basename(rel) in RESERVED:
        raise NoTopicsHere(rel, "not a note or a summary")
    text = read(vault, rel)
    fm, body = split_fm(text)
    if fm is None:
        raise NoTopicsHere(rel, "it has no header (run: frontmatter)")
    if fm_list(fm, "topics") == names:
        return False
    line = ["topics: [%s]" % ", ".join(ys(n) for n in names)]
    kind = fm_get(fm, "type")
    if kind == SUMMARY_TYPE and summary_in(vault, os.path.dirname(rel)) == rel:
        text = with_fm(assemble(fm, {"topics": line}, body), body)
    elif kind in AGENT_TYPES:
        text = set_fm_block(text, "topics", line, after=("tags", "description", "title", "type"))
    elif (fm_get(fm, "annotate") or "").lower() == "true":
        text = set_fm_block(text, "topics", line, after=("tags", "description", "generated"))
        fm = split_fm(text)[0]
        lines = annotated_lines(fm, by, at or now(), "topics")
        text = set_fm_block(text, "annotated", lines, after=("topics",))
    else:
        raise NoTopicsHere(rel, "its author hasn't allowed agent metadata (annotate: true)")
    write(vault, rel, text)
    return True
