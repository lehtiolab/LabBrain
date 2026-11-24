"""labbrain: keep an OKF v0.2 wiki conformant and current.

Spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
"""

import argparse
import os
import re
from pathlib import Path

from dotenv import dotenv_values

from .okf.check import check
from .okf.drift import RECHECK, drift_stamp, hot, is_due
from .okf.files import RESERVED, md_files, read, text_files, write
from .okf.frontmatter import content_hash, fm_get, split_fm
from .okf.git import commit, git_hashes
from .okf.index import OKF_VERSION, build_indexes
from .okf.links import carry_hashes, convert_links, name_index
from .okf.notes import add_frontmatter
from .okf.summaries import staleness, stamp, summaries, summary_in

COMMANDS = {
    "check": "Everything below; exit status 1 if anything is off.",
    "stale": "List stale summaries and why (changed/new/removed sources).",
    "stamp": "After rebuilding a folder summary: recompute its sources (with git blob hashes), "
    "children and parent, and set generated.by/at to now. Refuses any other file.",
    "index": "Regenerate every index.md from the notes and summaries. The map and related blocks "
    "(<!-- map:start --> … <!-- map:end -->, <!-- related:start --> … <!-- related:end -->) are "
    "agent-maintained and kept as they are.",
    "frontmatter": "Give notes without an OKF type a minimal block (type: Note, generated.by: "
    "ACTOR, and annotate: true on your own notes if LABBRAIN_ANNOTATE=true).",
    "links": "Rewrite [[wikilinks]] (and links Obsidian shortened to a bare file name) as relative "
    "markdown links, in every note or just FILE...; then carry each summary's recorded hashes "
    "forward, so a link-only edit doesn't read as stale or as a change since a drift check.",
    "hot": "Often-changed files that summaries are built from, the summary "
    "that hashes each and every agent-written file that links to it, and which are due a drift "
    "check.",
    "drift-stamp": "After a drift check of FILE: set its drift_verification entry in each SUMMARY, "
    "by default every summary that `hot` shows as due for FILE.",
    "commit": "At the end of a job: once check passes, stage and commit every change in each git "
    "repo of the vault, with ACTOR as the author. Never pushes: a person does that.",
}


# Settings about the person running labbrain, never about the wiki (docs/configuration.md).
SETTINGS = ("LABBRAIN_CONTRIBUTOR", "LABBRAIN_VAULT", "LABBRAIN_ANNOTATE")
# ponytail: the env file of the checkout labbrain runs from. An installed wheel has none, so it
# needs LABBRAIN_ENV; a per-user config folder is the upgrade if that becomes the common case.
ENV_FILE = Path(__file__).resolve().parents[2] / "env" / ".env"
CONTRIBUTOR_RE = re.compile(r"human:[^\s@]+")


def declares_okf(d):
    """True if folder d's index.md declares okf_version, which makes d a bundle root."""
    index = os.path.join(d, "index.md")
    if not os.path.isfile(index):
        return False
    with open(index, encoding="utf-8", errors="replace") as f:
        return bool(fm_get(split_fm(f.read())[0], "okf_version"))


def find_vault(start):
    """The outermost folder from start up (start included) whose index.md declares okf_version.
    Outermost, because a wiki can hold several bundles (one per git repo) and links cross them."""
    d, found = os.path.abspath(start), None
    while True:
        if declares_okf(d):
            found = d
        if os.path.dirname(d) == d:
            return found
        d = os.path.dirname(d)


class BadSetting(Exception):
    """A setting labbrain can't use."""

    def __init__(self, name, value, wanted):
        self.name, self.value, self.wanted = name, value, wanted
        super().__init__("bad setting %s=%s: wanted %s" % (name, value, wanted))


def settings(environ, env_file=ENV_FILE):
    """SETTINGS from the env file ($LABBRAIN_ENV, else env_file), each one overridden by environ;
    None where unset or empty, and LABBRAIN_ANNOTATE as a bool (unset: False)."""
    path = os.path.expanduser(environ.get("LABBRAIN_ENV") or str(env_file))
    if environ.get("LABBRAIN_ENV") and not os.path.exists(path):
        raise BadSetting("LABBRAIN_ENV", path, "an existing file")
    found = dotenv_values(path)
    for k in found:  # a typo would otherwise be ignored without a word
        if k.startswith("LABBRAIN_") and k not in SETTINGS:
            raise BadSetting(k, found[k], "one of %s (in %s)" % (", ".join(SETTINGS), path))
    out = {k: environ.get(k) or found.get(k) or None for k in SETTINGS}
    who, vault, annotate = (out[k] for k in SETTINGS)
    if who and not CONTRIBUTOR_RE.fullmatch(who):
        raise BadSetting("LABBRAIN_CONTRIBUTOR", who, "human:<name>, without an email address")
    if (annotate or "false").lower() not in ("true", "false"):
        raise BadSetting("LABBRAIN_ANNOTATE", annotate, "true or false")
    out["LABBRAIN_ANNOTATE"] = (annotate or "").lower() == "true"
    if out["LABBRAIN_ANNOTATE"] and not who:  # the preference is one person's, about their notes
        raise BadSetting("LABBRAIN_ANNOTATE", annotate, "LABBRAIN_CONTRIBUTOR set as well")
    if vault:
        out["LABBRAIN_VAULT"] = vault = os.path.abspath(os.path.expanduser(vault))
        if not declares_okf(vault):
            raise BadSetting(
                "LABBRAIN_VAULT", vault, "a folder whose index.md declares okf_version"
            )
    return out


class OutsideVault(Exception):
    """A file argument that resolves to a path outside the vault."""

    def __init__(self, path, vault):
        self.path, self.vault = path, vault
        super().__init__("not inside the vault %s: %s" % (vault, path))


def rel_arg(vault, p):
    """p, given relative to the working directory, as a vault-relative path."""
    rel = os.path.relpath(os.path.abspath(p), vault)
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        raise OutsideVault(p, vault)
    return rel


def parser():
    vault = argparse.ArgumentParser(add_help=False)
    # SUPPRESS: a subcommand that isn't given --vault must not overwrite one given before it.
    vault.add_argument(
        "--vault",
        default=argparse.SUPPRESS,
        metavar="DIR",
        help="the wiki's root folder (default: the outermost folder up from here whose index.md "
        "declares okf_version, else LABBRAIN_VAULT)",
    )
    p = argparse.ArgumentParser(
        prog="labbrain", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--vault", metavar="DIR", help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")
    cmds = {
        name: sub.add_parser(name, parents=[vault], help=text, description=text)
        for name, text in COMMANDS.items()
    }
    for name in ("stamp", "drift-stamp", "commit"):
        cmds[name].add_argument(
            "--by", metavar="ACTOR", help="who did it, e.g. claude-code/claude-opus-5-5"
        )
    cmds["frontmatter"].add_argument(
        "--by",
        metavar="ACTOR",
        help="the notes' author, as human:<name> (default: LABBRAIN_CONTRIBUTOR)",
    )
    cmds["commit"].add_argument("-m", "--message", help="the commit message")
    cmds["stamp"].add_argument("files", nargs="*", metavar="SUMMARY")
    cmds["links"].add_argument("files", nargs="*", metavar="FILE")
    cmds["drift-stamp"].add_argument("files", nargs="*", metavar="FILE [SUMMARY...]")
    cmds["hot"].add_argument("--days", type=int, default=30, help="window (default 30)")
    cmds["hot"].add_argument("--min", type=int, default=3, help="changes to be hot (default 3)")
    for name in ("hot", "drift-stamp"):
        cmds[name].add_argument(
            "--recheck",
            type=int,
            default=RECHECK,
            help="changes since a check that make it due (default %d)" % RECHECK,
        )
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help()
        return 2
    try:
        cfg = settings(os.environ)
    except BadSetting as e:
        print(e)
        return 2
    vault = args.vault or find_vault(os.getcwd()) or cfg["LABBRAIN_VAULT"]
    if not vault:
        print(
            "no vault found: run inside a wiki (a folder whose index.md declares okf_version), "
            "pass --vault DIR, or set LABBRAIN_VAULT"
        )
        return 2
    if not os.path.isdir(vault):
        print("no such folder:", vault)
        return 2
    vault = os.path.abspath(vault)
    cmd = args.cmd
    try:  # all of them before any command writes anything
        rest = [rel_arg(vault, p) for p in getattr(args, "files", [])]
    except OutsideVault as e:
        print(e)
        return 2

    if cmd == "check":
        problems = check(vault)
        for p, msg in problems:
            print("%s: %s" % (p, msg))
        print(
            "OK: vault is OKF %s conformant and current." % OKF_VERSION
            if not problems
            else "%d problem(s)." % len(problems)
        )
        return 1 if problems else 0
    if cmd == "stale":
        n = 0
        for s in summaries(vault):
            probs = staleness(vault, s)
            if probs:
                n += 1
                print(s)
                for kind, detail in probs:
                    print("    %-8s %s" % (kind, detail))
        print("%d stale summary(ies)." % n)
        return 1 if n else 0
    if cmd == "stamp":
        if not args.by or not rest:
            print("usage: stamp --by ACTOR SUMMARY...   (e.g. --by claude-code/claude-opus-5-5)")
            return 2
        # Anything else would get a summary's bookkeeping: the folder's sources, and the actor in
        # place of a note's author. All are checked before any is written.
        wrong = [p for p in rest if summary_in(vault, os.path.dirname(p)) != p]
        for p in wrong:
            print("not a folder summary, so not stamped:", p)
        if wrong:
            return 2
        for p in rest:
            stamp(vault, p, args.by)
            print("stamped", p)
        return 0
    if cmd == "index":
        for rel in build_indexes(vault):
            print("wrote", rel)
        return 0
    if cmd == "frontmatter":
        by = args.by or cfg["LABBRAIN_CONTRIBUTOR"]
        if not by:
            print(
                "usage: frontmatter --by ACTOR   (the notes' author, e.g. --by human:<name>; "
                "or set LABBRAIN_CONTRIBUTOR)"
            )
            return 2
        # Your preference goes only into notes signed as you, never into someone else's.
        annotate = cfg["LABBRAIN_ANNOTATE"] and by == cfg["LABBRAIN_CONTRIBUTOR"]
        for p in md_files(vault):
            if (
                os.path.basename(p) not in RESERVED
                and not p.endswith("_summary.md")
                and add_frontmatter(vault, p, by, annotate)
            ):
                print("added frontmatter:", p)
        return 0
    if cmd == "links":
        idx = name_index(vault)
        before = git_hashes(vault, text_files(vault))
        before_content = {s: content_hash(read(vault, s)) for s in summaries(vault)}
        targets = rest or [p for p in md_files(vault) if os.path.basename(p) not in RESERVED]
        for p in targets:
            text = read(vault, p)
            new, missing = convert_links(vault, p, text, idx)
            if new != text:
                write(vault, p, new)
                print("rewrote links:", p)
            for name in missing:
                print("  unresolved in %s: %s" % (p, name))
        for s in carry_hashes(vault, before, before_content):
            print("carried hashes forward:", s)
        return 0
    if cmd == "hot":
        days, least, recheck = args.days, args.min, args.recheck
        rows = hot(vault, days, least, recheck)
        print(
            "%d hot file(s): %d or more changes in the last %d days "
            "(commits, plus 1 for uncommitted edits)." % (len(rows), least, days)
        )
        print(
            "%d due for a drift check: a summary never checked against it, or %d or more changes "
            "to the file and edits to the summary since its check."
            % (sum(is_due(r[6]) for r in rows), recheck)
        )

        def drift(c):
            kind, e, k, due = c
            if kind == "record":
                return "session summary: never checked"
            if kind == "untagged":
                return "no tag: checked when the file is due"
            if not e:
                return "never checked: DUE"
            return "checked %s, %d change%s since%s%s" % (
                e.get("at", "?")[:10],
                k[0],
                "" if k[0] == 1 else "s",
                " + %d summary edit%s" % (k[1], "" if k[1] == 1 else "s") if k[1] else "",
                ": DUE" if due else "",
            )

        for p, n, dirty, s, status, refs, checks in rows:
            print(
                "\n%3d  %s   (%d commit(s)%s)   %s"
                % (
                    n + dirty,
                    p,
                    n,
                    " + uncommitted" if dirty else "",
                    "DUE" if is_due(checks) else "skip: checked",
                )
            )
            print(
                "       summary   %s"
                % (
                    "%s (%s; %s)" % (s, status, drift(checks[s]))
                    if s
                    else "none: no summary hashes it"
                )
            )
            for f, k in sorted(refs.items()):
                print(
                    "       cited by  %s (%d link%s; %s)"
                    % (f, k, "s" if k > 1 else "", drift(checks[f]))
                )
        return 0
    if cmd == "drift-stamp":
        if not args.by or not rest:
            print("usage: drift-stamp --by ACTOR FILE [SUMMARY...]   (after a drift check of FILE)")
            return 2
        p = rest[0]
        if not os.path.isfile(os.path.join(vault, p)):
            print("no such file:", p)
            return 2
        files = rest[1:] or None
        stamped, refused = drift_stamp(vault, p, args.by, files, args.recheck)
        for f in stamped:
            print("drift-stamped", f)
        for f in refused:
            print("  not a summary, no tag:", f)
        if not stamped and not refused:
            print("nothing due for", p)
        return 1 if refused else 0
    if cmd == "commit":
        if not args.by or not args.message:
            print("usage: commit --by ACTOR -m MESSAGE   (e.g. --by claude-code/claude-opus-5-5)")
            return 2
        if "@" in args.by:
            print("an actor is a tool or a person, never an email address:", args.by)
            return 2
        problems = check(vault)
        for p, msg in problems:
            print("%s: %s" % (p, msg))
        if problems:
            print("%d problem(s), so nothing was committed." % len(problems))
            return 1
        done = commit(vault, args.by, args.message)
        for repo, short in done:
            print("committed %s in %s" % (short, repo or "."))
        if not done:
            print("nothing to commit")
        return 0
    return 2
