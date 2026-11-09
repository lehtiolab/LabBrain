"""Skills and pattern examples: their frontmatter, and the commands the skills tell agents
to run."""

import json
import re
from pathlib import Path

import pytest

from labbrain.cli import COMMANDS
from labbrain.okf.frontmatter import fm_get, fm_list, split_fm

ROOT = Path(__file__).parent.parent
# skills/ is for agents working on a wiki; dev-skills/ for agents working on this repo.
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md")) + sorted(
    (ROOT / "dev-skills").glob("*/SKILL.md")
)
# A command is written in backticks: `labbrain stale`. Prose ("labbrain does …") isn't one.
COMMAND = re.compile(r"`labbrain ([a-z][a-z-]*)")


def test_there_are_skills():
    assert {p.parent.name for p in SKILLS} >= {
        "search",
        "okf-conventions",
        "summary-writing",
        "index",
        "drift",
        "update-docs",
    }


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter(path):
    """The SKILL.md format: name matches its folder (lowercase, hyphens), a description that says
    what the skill does and when to use it, at most 1024 characters."""
    fm, body = split_fm(path.read_text(encoding="utf-8"))
    assert fm is not None, "no frontmatter"
    assert fm_get(fm, "name") == path.parent.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", path.parent.name)
    assert 0 < len(fm_get(fm, "description") or "") <= 1024
    assert body.strip()


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_commands_exist(path):
    """A skill and the code it calls change together: a renamed command fails here."""
    named = set(COMMAND.findall(path.read_text(encoding="utf-8")))
    assert named - set(COMMANDS) == set()


def test_pattern_examples():
    traces = {}
    for line in (ROOT / "patterns/examples/2026-01-05.jsonl").read_text().splitlines():
        record = json.loads(line)
        if "feedback_for" in record:
            assert record["feedback_for"] in traces
        else:
            assert {"id", "at", "job", "skill", "skill_version", "actor", "outcome"} <= set(record)
            traces[record["id"]] = record
    for path in (ROOT / "patterns/examples").glob("*.md"):
        fm, _ = split_fm(path.read_text(encoding="utf-8"))
        assert fm_get(fm, "type") == "Pattern"
        assert set(fm_list(fm, "evidence")) <= set(traces)
