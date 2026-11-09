"""check: everything at once."""

import os
import re

from .files import is_repo_root, join, md_files, read
from .frontmatter import fm_blocks, fm_drift, fm_get, split_fm
from .index import build_indexes, index_targets
from .links import link_problems
from .notes import agent_files
from .summaries import staleness, summaries


def check(vault):
    problems = []
    for p in md_files(vault):
        base = os.path.basename(p)
        fm, body = split_fm(read(vault, p))
        if base == "index.md":
            allowed = is_repo_root(vault, os.path.dirname(p))
            if fm is not None and not (
                allowed and set(k for k, _ in fm_blocks(fm) if k) <= {"okf_version"}
            ):
                problems.append(
                    (p, "index.md may only carry okf_version, and only at a bundle root")
                )
        elif base == "log.md":
            bad = [
                h
                for h in re.findall(r"^## (.+)$", body, re.M)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", h.strip())
            ]
            if bad:
                problems.append((p, "log.md date headings must be YYYY-MM-DD: " + ", ".join(bad)))
        elif fm is None:
            problems.append((p, "no frontmatter (run: frontmatter)"))
        elif not fm_get(fm, "type"):
            problems.append((p, "frontmatter has no type (run: frontmatter)"))
    for s in summaries(vault):
        for kind, detail in staleness(vault, s):
            problems.append((s, "stale: %s %s" % (kind, detail)))
        here = os.path.dirname(s)
        for e in fm_drift(split_fm(read(vault, s))[0]):
            if not os.path.exists(os.path.join(vault, here, e.get("resource", ""))):
                problems.append(
                    (
                        s,
                        "drift_verification names a missing file: %s (run: links)"
                        % e.get("resource"),
                    )
                )
    for rel in build_indexes(vault, dry=True):
        problems.append((rel, "out of date (run: index)"))
    # Every note uses markdown links. Broken ones are only checked in agent-written files: a raw
    # note may link a note that isn't written yet (OKF allows it).
    agent = set(agent_files(vault) + [join(d, "index.md") for d in index_targets(vault)])
    for p in md_files(vault):
        if os.path.basename(p) != "log.md" and (p in agent or os.path.basename(p) != "index.md"):
            for msg in link_problems(vault, p, broken=p in agent):
                problems.append((p, msg + (" (run: links)" if msg.startswith("wikilink") else "")))
    return problems
