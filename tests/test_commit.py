"""labbrain commit: a job's work, committed in each repo of the wiki, never pushed."""

import re
import subprocess
from pathlib import Path

from conftest import git

from labbrain.cli import main

BUNDLE = '---\nokf_version: "0.2"\n---\n'
NOTE = "---\ntype: Note\n---\n# %s\n"


def out(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def wiki(tmp_path):
    """A conformant wiki of two repos. Lab/ is a repo inside the root one, and not gitignored."""
    w = tmp_path / "wiki"
    lab = w / "Lab"
    lab.mkdir(parents=True)
    for repo, name in ((w, "Garden"), (lab, "Bench")):
        (repo / "index.md").write_text(BUNDLE)
        (repo / ("%s.md" % name)).write_text(NOTE % name)
    for repo in (lab, w):
        git(repo, "init", "-q", "-b", "main")
    assert main(["index", "--vault", str(w)]) == 0
    for repo in (lab, w):
        git(repo, "add", "-A", "--", ".", ":(exclude)Lab")
        git(repo, "commit", "-q", "-m", "notes")
    return w, lab


def test_commits_each_repo_as_the_actor(tmp_path, git_env, capsys):
    w, lab = wiki(tmp_path)
    (w / "Garden.md").write_text(NOTE % "Garden" + "Watered.\n")
    (lab / "Bench.md").write_text(NOTE % "Bench" + "Cleaned.\n")
    capsys.readouterr()
    assert main(["commit", "--by", "agent/test", "-m", "index run", "--vault", str(w)]) == 0
    printed = capsys.readouterr().out
    for repo, where in ((w, "."), (lab, "Lab")):
        assert (
            out(repo, "log", "-1", "--format=%an <%ae>|%s") == "agent/test <agent/test>|index run\n"
        )
        assert out(repo, "status", "--porcelain", "--", ".", ":(exclude)Lab") == ""
        assert "in %s\n" % where in printed
    assert "Lab" not in out(w, "ls-tree", "--name-only", "HEAD").split()


def test_nothing_to_commit(tmp_path, git_env, capsys):
    w, _ = wiki(tmp_path)
    head = out(w, "rev-parse", "HEAD")
    assert main(["commit", "--by", "agent/test", "-m", "quiet night", "--vault", str(w)]) == 0
    assert capsys.readouterr().out.endswith("nothing to commit\n")
    assert out(w, "rev-parse", "HEAD") == head


def test_refuses_while_check_fails(vault, git_env, capsys):
    """The fixture vault has stale summaries and notes without headers."""
    head, status = out(vault, "rev-parse", "HEAD"), out(vault, "status", "--porcelain")
    assert main(["commit", "--by", "agent/test", "-m", "early", "--vault", str(vault)]) == 1
    assert "nothing was committed" in capsys.readouterr().out
    assert (out(vault, "rev-parse", "HEAD"), out(vault, "status", "--porcelain")) == (head, status)


def test_needs_an_actor_and_a_message(tmp_path, git_env):
    w, _ = wiki(tmp_path)
    assert main(["commit", "-m", "who?", "--vault", str(w)]) == 2
    assert main(["commit", "--by", "agent/test", "--vault", str(w)]) == 2
    assert main(["commit", "--by", "ada@example.org", "-m", "x", "--vault", str(w)]) == 2


def test_nothing_pushes():
    """Agents commit and a person pushes (AGENT.md)."""
    src = Path(__file__).parent.parent / "src"
    pushes = [p for p in src.rglob("*.py") if re.search(r"""["']push["']""", p.read_text())]
    assert pushes == []
