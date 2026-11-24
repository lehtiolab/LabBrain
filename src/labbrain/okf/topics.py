"""Topics from the wiki's vocabulary, set on a file's header: a summary or another agent-written
file, or a raw note whose author allows agent metadata (`annotate: true`).

The model chooses the topics; this code checks them against topics.yaml and writes them, with the
`annotated` entry OKF asks for on a raw note (skills/okf-conventions).
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


class NotTopics(Exception):
    """Words that name no topic in the wiki's vocabulary."""

    def __init__(self, words):
        self.words = words
        super().__init__(
            "not in topics.yaml: %s (nothing was written; propose them to a person)"
            % ", ".join(words)
        )


class NoTopicsHere(Exception):
    """A file whose header labbrain won't give topics."""

    def __init__(self, path, why):
        self.path, self.why = path, why
        super().__init__("topics not set on %s: %s" % (path, why))


def canonical(words, topics):
    """Each word as the topic it names, itself or by a synonym, in order, each once."""
    names = {}
    for name, t in topics.items():
        for w in (name, *t["synonyms"]):
            names.setdefault(w.lower(), name)
    unknown = [w for w in words if w.lower() not in names]
    if unknown:
        raise NotTopics(unknown)
    return list(dict.fromkeys(names[w.lower()] for w in words))


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
    """Write topics (checked by canonical()) into rel's header. True if the file changed.

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
