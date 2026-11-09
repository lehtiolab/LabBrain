"""Drift checks, called in-process as a night run would: one process, several jobs."""

from conftest import NOW, append, git

from labbrain.okf.drift import drift_stamp, hot

TOMATOES = "Garden/Tomatoes.md"


def check_of(rows, path, summary):
    """The (kind, entry, (changes, edits), due) a hot() row holds for summary."""
    return next(r for r in rows if r[0] == path)[6][summary]


def test_history_is_read_again_after_a_commit(vault, git_env):
    """The checked version was never committed; two commits since then count as two changes."""
    drift_stamp(vault, TOMATOES, "agent/test", ["Garden/Garden_summary.md"])
    hot(vault, 30, 3)  # reads Tomatoes' history before the commits below
    for week, later in ((3, 3600), (4, 7200)):
        append(vault / TOMATOES, f"\nWeek {week}: picked.\n")
        git(vault, "commit", "-q", "-am", f"week {week}", at=NOW + later)
    _, _, (changes, edits), due = check_of(hot(vault, 30, 3), TOMATOES, "Garden/Garden_summary.md")
    assert (changes, edits, due) == (2, 0, False)
