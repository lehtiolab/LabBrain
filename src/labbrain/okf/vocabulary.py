"""The wiki's vocabulary, grown from its files: the topics their headers use go into topics.yaml,
with status: new, for people to review. Code only.

topics.yaml is only ever added to, so what people wrote there (synonyms, narrower topics,
statuses, comments) stays as it is (docs/configuration.md).
"""

import difflib
import os

import yaml

from .config import BadWikiConfig
from .files import RESERVED, TOPICS, md_files, read, write
from .frontmatter import fm_list, split_fm
from .topics import as_topic, topic_names

HEADER = """\
# The wiki's vocabulary. `labbrain vocabulary` adds the topics the files use, with status: new.
# People review them: add synonyms and narrower topics, merge a topic into another by making it one
# of its synonyms, or veto it with status: vetoed (docs/configuration.md).
"""
CLOSE = 0.85  # how alike two spellings must be to be shown as a possible duplicate


def in_use(vault):
    """{topic as a file writes it: [files]}, for every topic in a header."""
    out = {}
    for p in md_files(vault):
        if os.path.basename(p) not in RESERVED:
            for t in fm_list(split_fm(read(vault, p))[0], "topics"):
                out.setdefault(t, []).append(p)
    return out


def unlisted(used, topics):
    """The topics in used that topics.yaml names neither as a topic nor as a synonym, sorted, as
    topics are written: lower case, with hyphens."""
    return sorted({as_topic(w) for w in used} - set(topic_names(topics)) - {""})


def add_topics(vault, names, topics):
    """Add names to the end of topics.yaml, each with status: new. Nothing already there changes."""
    path = os.path.join(vault, TOPICS)
    old = read(vault, TOPICS) if os.path.exists(path) else HEADER
    old += "" if not old or old.endswith("\n") else "\n"
    block = {n: {"status": "new"} for n in names}
    text = old + yaml.safe_dump(
        block, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    try:  # a file written as one flow mapping can't be added to
        ok = {str(k) for k in yaml.safe_load(text) or {}} == set(topics) | set(names)
    except yaml.YAMLError:
        ok = False
    if not ok:
        raise BadWikiConfig(TOPICS, "the file", "one topic per line at the top level, to add to")
    write(vault, TOPICS, text)


def close_spellings(topics):
    """(new topic, word, the word's topic) for each new topic spelled like a name or a synonym of
    another topic, each pair once: a possible duplicate, for a person to merge or keep."""
    words = {
        as_topic(w): n
        for n, t in topics.items()
        if t.get("status") != "vetoed"
        for w in (n, *t["synonyms"])
    }
    out, seen = [], set()
    for n, t in topics.items():
        if t.get("status") == "new":
            others = [w for w, m in words.items() if m != n]
            for w in difflib.get_close_matches(as_topic(n), others, 3, CLOSE):
                if frozenset((n, words[w])) not in seen:
                    seen.add(frozenset((n, words[w])))
                    out.append((n, w, words[w]))
    return out


def vetoed_in_use(used, topics):
    """{vetoed topic: [files]} for the vetoed topics that files still carry."""
    named, out = topic_names(topics), {}
    for w, files in used.items():
        n = named.get(as_topic(w))
        if n and topics[n].get("status") == "vetoed":
            out.setdefault(n, set()).update(files)
    return {n: sorted(f) for n, f in sorted(out.items())}
