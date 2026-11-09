"""Raw notes and concept types: minimal frontmatter, and which files are agent-written."""

import os
import re

from .files import RESERVED, md_files, read, write
from .frontmatter import fm_get, split_fm, with_fm, ys
from .summaries import SUMMARY_TYPE

# Concepts an agent drafts from a published paper, in a paper bundle
PAPER_TYPES = ("Paper", "Method", "Algorithm", "Finding", "Dataset", "Software", "Reference")
AGENT_TYPES = (SUMMARY_TYPE, "Agent Guide", "Session Summary") + PAPER_TYPES


def add_frontmatter(vault, rel, by, annotate):
    """Give a note a minimal OKF block without touching its body; with annotate, also
    `annotate: true`, its author's consent to metadata added by agents. True if changed."""
    text = read(vault, rel)
    nl = "\r\n" if "\r\n" in text else "\n"
    fm, body = split_fm(text)
    consent = ["annotate: true"] if annotate else []
    if fm is None:
        write(
            vault,
            rel,
            with_fm(["type: Note", "generated: { by: %s }" % ys(by)] + consent, text, nl),
        )
        return True
    if fm_get(fm, "type"):
        return False
    add = ["type: Note"]
    if not re.search(r"^generated\s*:", fm, re.M):
        add.append("generated: { by: %s }" % ys(by))
    if not re.search(r"^annotate\s*:", fm, re.M):  # the author's own answer stands
        add += consent
    head = re.match(r"---[ \t]*\r?\n", text).end()
    write(vault, rel, text[:head] + nl.join(add) + nl + text[head:])
    return True


def note_type(vault, rel):
    fm, _ = split_fm(read(vault, rel))
    return fm_get(fm, "type") if fm is not None else None


def agent_files(vault):
    return [
        p
        for p in md_files(vault)
        if os.path.basename(p) not in RESERVED and note_type(vault, p) in AGENT_TYPES
    ]
