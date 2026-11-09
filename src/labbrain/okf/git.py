"""The git calls: blob hashes, history, and the repos inside the vault."""

import os
import subprocess
from datetime import datetime

from .files import is_repo_root, join, walk


def git_hashes(vault, rels):
    """git hash-object for many vault-relative files at once."""
    if not rels:
        return {}
    out = subprocess.run(
        ["git", "hash-object", "--stdin-paths"],
        cwd=vault,
        check=True,
        input="\n".join(rels) + "\n",
        capture_output=True,
        text=True,
    ).stdout.split()
    return dict(zip(rels, out))


def repos(vault):
    """The git repos in the vault, as vault-relative folders ('' is the root)."""
    return [d for d, _, _ in walk(vault) if os.path.exists(os.path.join(vault, d, ".git"))]


def commit(vault, actor, message):
    """Stage and commit every change in each repo of the vault, authored by actor; never pushes.
    [(repo, short hash)] for the repos that had changes. A repo inside another is left out of it,
    so the outer repo never records it as an embedded repo."""
    found, done = repos(vault), []
    for repo in found:
        inner = [r for r in found if r != repo and (not repo or r.startswith(repo + os.sep))]
        exclude = [":(exclude,literal)" + os.path.relpath(r, repo or ".") for r in inner]

        def git(*args):
            return subprocess.run(
                ["git", *args],
                cwd=os.path.join(vault, repo),
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        git("add", "-A", "--", ".", *exclude)
        if not git("diff", "--cached", "--name-only"):
            continue
        # The actor stands in for the email too: no email address goes in a commit.
        git(
            *("-c", "user.name=" + actor, "-c", "user.email=" + actor),
            *("commit", "-q", "--author", "%s <%s>" % (actor, actor), "-m", message),
        )
        done.append((repo, git("rev-parse", "--short", "HEAD").strip()))
    return done


def git_paths(vault, repo, *args):
    """NUL-separated paths from a git command run with -z, as vault-relative paths."""
    out = subprocess.run(
        ["git", *args], cwd=os.path.join(vault, repo), capture_output=True, text=True
    ).stdout
    return [t.strip("\n") for t in out.split("\0") if t.strip("\n")]


def changes(vault, days):
    """vault path -> (commits touching it in the last `days` days,
    True if it has uncommitted edits)."""
    commits, dirty = {}, set()
    for repo in repos(vault):
        for p in git_paths(
            vault, repo, "log", "-z", "--since=%d.days" % days, "--name-only", "--format="
        ):
            commits[join(repo, p)] = commits.get(join(repo, p), 0) + 1
        entries = git_paths(vault, repo, "status", "--porcelain", "-z", "-uall")
        skip = False
        for e in entries:
            if skip:  # the original path of a rename or copy
                skip = False
                continue
            dirty.add(join(repo, e[3:]))
            skip = e[0] in "RC"
    return {p: (commits.get(p, 0), p in dirty) for p in set(commits) | dirty}


def owning_repo(vault, rel):
    d = os.path.dirname(rel)
    while not is_repo_root(vault, d):
        d = os.path.dirname(d)
    return d


def history(vault, rel, cache):
    """[(commit, date, blob)] for the commits that changed rel, newest first
    (blob None once deleted). cache (rel -> rows) belongs to one call: a commit made after it
    was filled is not in it."""
    if rel not in cache:
        repo = owning_repo(vault, rel)
        out = subprocess.run(
            [
                "git",
                "log",
                "--format=%x01%H %cI",
                "--raw",
                "--no-abbrev",
                "--",
                os.path.relpath(rel, repo or "."),
            ],
            cwd=os.path.join(vault, repo),
            capture_output=True,
            text=True,
        ).stdout
        rows = []
        for chunk in out.split("\x01")[1:]:
            lines = chunk.strip("\n").split("\n")
            commit, date = lines[0].split()
            raw = [line.split()[3] for line in lines[1:] if line.startswith(":")]
            blob = raw[0] if raw and raw[0].strip("0") else None
            rows.append((commit[:7], iso(date), blob))
        cache[rel] = rows
    return cache[rel]


def blob_text(vault, rel, blob):
    out = subprocess.run(
        ["git", "cat-file", "-p", blob],
        cwd=os.path.join(vault, owning_repo(vault, rel)),
        capture_output=True,
    ).stdout
    return out.decode("utf-8", "replace")


def iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
