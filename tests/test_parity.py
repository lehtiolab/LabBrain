"""The package does what okf_vault.sh does: same output, exit status and files, per command.

Each case runs the reference script on one copy of the dummy vault and the package on another.
Timestamps are masked, since the two runs read the clock a moment apart.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ENV, NOW, REFERENCE, append, git

REF = ["sh", str(REFERENCE)]
PACKAGE = [sys.executable, "-m", "labbrain"]
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def run(prefix, vault, args):
    p = subprocess.run(
        [*prefix, *args, "--vault", str(vault)], cwd=vault, env=ENV, capture_output=True, text=True
    )
    return p.returncode, TIME.sub("<TIME>", p.stdout)


def snapshot(vault):
    """Every file outside .git, timestamps masked."""
    files = {}
    for root, dirs, names in os.walk(vault):
        dirs[:] = [d for d in dirs if d != ".git"]
        for n in names:
            p = Path(root, n)
            text = p.read_bytes().decode("utf-8", "replace")
            files[str(p.relative_to(vault))] = TIME.sub("<TIME>", text)
    return files


@pytest.fixture
def pair(vault_template, tmp_path):
    return tuple(
        Path(shutil.copytree(vault_template, tmp_path / n, symlinks=True)) for n in ("ref", "pkg")
    )


def same(pair, *args):
    ref, pkg = pair
    want = run(REF, ref, args)
    assert run(PACKAGE, pkg, args) == want, args
    assert snapshot(pkg) == snapshot(ref), args
    return want


BY = ("--by", "agent/test")
SINGLE = [
    ("check",),
    ("stale",),
    ("stamp", *BY, "Garden/Garden_summary.md"),
    ("stamp", *BY, "Garden/Garden_summary.md", "Garden/Soil/Soil_summary.md"),
    ("stamp", "Garden/Garden_summary.md"),  # no --by: usage
    ("stamp", *BY),  # no summary: usage
    ("index",),
    ("frontmatter", "--by", "human:tester"),
    ("links",),
    ("links", "Garden/Fresh.md"),
    ("hot",),
    ("hot", "--days", "365", "--min", "1", "--recheck", "1"),
    ("drift-stamp", *BY, "Garden/Tomatoes.md"),
    ("drift-stamp", *BY, "Garden/Beans.md", "Garden/Garden_summary.md"),
    ("drift-stamp", *BY, "Garden/Tomatoes.md", "Kitchen/Session_2026-01-05.md"),  # refused
    ("drift-stamp", *BY, "Garden/Nope.md"),  # no such file
    ("drift-stamp", "Garden/Tomatoes.md"),  # no --by: usage
]


@pytest.mark.parametrize("args", SINGLE, ids=" ".join)
def test_command(pair, args):
    same(pair, *args)


def test_reference_sees_the_fixture(pair):
    """Guards the fixture: the cases above are only worth something if these paths are hit."""
    code, out = run(REF, pair[0], ["check"])
    assert code == 1
    for expect in (
        "Garden/Beans.md: no frontmatter",
        "stale: changed Tomatoes.md",
        "stale: new Fresh.md",
        "wikilink [[Beans]]",
        "broken Brine.md",
        "log.md date headings must be YYYY-MM-DD: Jan 5",
        "Kitchen/Shopping.md: frontmatter has no type",
    ):
        assert expect in out, expect
    code, out = run(REF, pair[0], ["hot"])
    assert "Garden/Tomatoes.md" in out and "never checked: DUE" in out


def test_sequence(pair):
    """A night's work in order, so each command reads what the one before it wrote."""
    for args in [
        ("check",),
        ("stale",),
        ("drift-stamp", *BY, "Garden/Beans.md", "Garden/Garden_summary.md"),
        ("frontmatter", "--by", "human:tester"),
        ("links",),  # carries the Beans hash forward, in sources and in drift_verification
        ("stale",),
        ("stamp", *BY, "Garden/Garden_summary.md"),
        ("index",),
        ("check",),
        ("hot",),
        ("drift-stamp", *BY, "Garden/Tomatoes.md"),
        ("hot",),
    ]:
        same(pair, *args)
    later = NOW + 3600  # after the drift check, and the same commit in both copies
    for vault in pair:
        append(vault / "Garden" / "Tomatoes.md", "\nWeek 3: picked.\n")
        git(vault, "commit", "-q", "-m", "week 3", "--", "Garden/Tomatoes.md", at=later)
    for args in [("hot",), ("hot", "--recheck", "1")]:
        same(pair, *args)
    for vault in pair:  # an edit to the summary itself also counts toward the next check
        append(vault / "Garden" / "Garden_summary.md", "\n- Week 3 was picked.\n")
        git(vault, "commit", "-q", "-m", "summary", "--", "Garden/Garden_summary.md", at=later + 60)
    for args in [("hot",), ("check",)]:
        same(pair, *args)
