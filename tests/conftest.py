"""A dummy vault with git history, built once per session from tests/fixtures/vault."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "vault"
REFERENCE = HERE / "reference" / "okf_vault.sh"
NOW = int(time.time())
DAY = 86400

# No GIT_* from the caller (a hook's GIT_DIR would point every command at this repo), no
# global or system config (signing, hooks, aliases), and a dummy identity, never a real one.
# No LABBRAIN_* either, and an empty settings file: a test never reads your env/.env.
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "LABBRAIN_"))}
ENV.update(
    LABBRAIN_ENV=os.devnull,
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="Test",
    GIT_AUTHOR_EMAIL="test@example.org",
    GIT_COMMITTER_NAME="Test",
    GIT_COMMITTER_EMAIL="test@example.org",
    TZ="UTC",
    # The reference script runs `python3` from PATH: make it the interpreter under test.
    PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
)


def git(repo, *args, at=None):
    """Run git in repo; `at` (epoch seconds) dates the commit."""
    env = (
        ENV
        if at is None
        else {**ENV, "GIT_AUTHOR_DATE": f"{at} +0000", "GIT_COMMITTER_DATE": f"{at} +0000"}
    )
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def reference(vault, *args):
    """Run the unchanged okf_vault.sh on vault."""
    return subprocess.run(
        ["sh", str(REFERENCE), *args, "--vault", str(vault)],
        cwd=vault,
        env=ENV,
        check=True,
        capture_output=True,
        text=True,
    )


def append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


@pytest.fixture(scope="session")
def vault_template(tmp_path_factory):
    """A vault mid-life: summaries stamped 19 days ago, one note edited since (committed twice,
    then uncommitted), one new untracked note, and a sub-repo (Shelf/) with its own history."""
    vault = tmp_path_factory.mktemp("template") / "vault"
    shutil.copytree(FIXTURE, vault)
    (vault / ".gitignore").write_text("Shelf/\n")  # here, not in FIXTURE: it would hide Shelf/
    (vault / "Garden" / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    shelf = vault / "Shelf"
    for repo in (vault, shelf):
        git(repo, "init", "-q", "-b", "main")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "notes", at=NOW - 20 * DAY)
    reference(
        vault,
        "stamp",
        "--by",
        "agent/test",
        "Garden/Garden_summary.md",
        "Garden/Soil/Soil_summary.md",
        "Shelf/Shelf_summary.md",
    )
    reference(vault, "index")
    for repo in (vault, shelf):
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "summaries", at=NOW - 19 * DAY)
    tomatoes = vault / "Garden" / "Tomatoes.md"
    for week, days in ((1, 12), (2, 6)):
        append(tomatoes, f"\nWeek {week}: watered twice.\n")
        git(vault, "commit", "-q", "-am", f"week {week}", at=NOW - days * DAY)
    append(shelf / "Jars.md", "\nTwo more jars filled.\n")
    git(shelf, "commit", "-q", "-am", "jars", at=NOW - 5 * DAY)
    append(tomatoes, "\nToday: first ripe fruit.\n")
    (vault / "Garden" / "Fresh.md").write_text(
        "# Fresh\nJust started. Links to [[Beans]] and [Recipes](Recipes.md).\n"
    )
    return vault


@pytest.fixture
def vault(vault_template, tmp_path):
    """A fresh copy of the template vault, git history included."""
    return Path(shutil.copytree(vault_template, tmp_path / "vault", symlinks=True))


@pytest.fixture(autouse=True)
def no_user_settings(monkeypatch):
    """In-process calls read os.environ: keep the caller's LABBRAIN_* and env/.env out of them."""
    for k in [k for k in os.environ if k.startswith("LABBRAIN_")]:
        monkeypatch.delenv(k)
    monkeypatch.setenv("LABBRAIN_ENV", os.devnull)


@pytest.fixture
def git_env(monkeypatch):
    """ENV for in-process calls, whose git subprocesses inherit os.environ."""
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(k)
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)
