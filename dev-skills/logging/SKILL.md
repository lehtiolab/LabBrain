---
name: logging
description: Write a decision to LabBrain's audit log with the hash of the commit that holds its work, and fill in the hash of entries still marked uncommitted. Use when asked to log a decision, when a major decision or discovery has been made, and when the session-start check in AGENT.md lists pending entries. Commits locally; never pushes.
---

# logging: every audit-log entry names its commit

This skill is for working on the LabBrain repo. The log is `logs/audit_log.md`; the check is
`sh dev-skills/logging/pending.sh`.

## Why
The hash is what makes an entry checkable: the commit exists and holds what the entry says. A
hash exists only once its commit does, and decisions are usually taken before the commit. An
entry written first says `uncommitted`, and an `uncommitted` entry is a decision whose work may
not be in git at all. The check brings it back each session until it names its commit.

## Rules
- **Never push.** Not after a commit, not to finish the job, not when asked to log. Pushing is the
  user's.
- **Never commit on `main`.** Work reaches `main` only by pull request from a `feat/` branch. If
  `git branch --show-current` says `main`, stop and ask which `feat/<topic>` branch to use, then
  `git switch -c feat/<topic>`; uncommitted work comes with it.
- **Commit only what the decision touched.** Stage named paths, `git add -- <path>…`; never
  `git add -A`, `git add .` or `git commit -a`. Unrelated changes stay unstaged. If one file holds
  both, ask before staging it.
- **Never amend, rebase, squash or reset.** A rewritten commit orphans every hash already logged.
- **Never `--no-verify`.** A failing hook stops the commit; report it, and the entry stays
  `uncommitted`.
- **The hash is the work's commit,** read with `git rev-parse --short HEAD` straight after it. The
  entry then goes in a commit of its own, so the log is always one commit behind the work it
  names.
- **A decision that changed no tracked file** takes the hash of `HEAD` and says so:
  `## YYYY-MM-DD — <hash> (no tracked file changed) — <title>`.
- **Filling in a hash is the one edit allowed to an existing entry.** Nothing else in it changes.
- AGENT.md's rules on commits still hold: read `git status` first; no data, secrets or generated
  files.

## Entry format
The header is `## YYYY-MM-DD — <hash> — <title>`, with `uncommitted` in place of the hash until
the commit exists. The body follows the template at the top of the log. Entries go at the end,
newest last.

## At session start
AGENT.md has you run `sh dev-skills/logging/pending.sh` before anything else.
- **Exit 0:** nothing pending; say nothing.
- **Exit 1:** tell the user *"There are uncommitted decisions in the audit log"*, list the lines
  it printed, and stop. Do not resolve them unasked.
- **Exit 2:** it could not check (no log, not a repo); say so.

On the user's go-ahead, resolve them (below).

## Logging a decision
When asked to log a decision, being asked is the go-ahead to commit it.
1. `git status` and `git diff`: list the paths that belong to the decision.
2. Commit them: `git add -- <paths>`, then `git commit -m "<title>"`.
3. `git rev-parse --short HEAD` is the hash.
4. Append the entry to `logs/audit_log.md` with that hash.
5. Commit the log alone: `git add -- logs/audit_log.md`, `git commit -m "audit log: <title>"`.
6. Run the check; it exits 0.
7. Report both hashes and anything left unstaged. Do not push.

If the work can't be committed yet (the user says not yet, the tests fail, a hook refuses),
append the entry as `uncommitted` and stop; the next session's check brings it back.

## Resolving `uncommitted` entries
For each line the check printed:
1. Read the entry and work out which files it describes.
2. **Already committed?** `git log --oneline -- <paths>`, then `git show --stat <hash>` on each
   candidate. One commit that holds the work is the hash.
3. **Still in the working tree?** Commit it as in *Logging a decision*, steps 1–3.
4. **Neither, or several commits and no clear one?** Don't guess a hash. Tell the user what you
   found and leave the entry as it is.
5. Replace `uncommitted` in the header with the hash. A `no commit <hash> here` line (a typo, or
   history that was rewritten) is fixed the same way, once the right commit is known.

Then commit the log once for all of them, `audit log: hashes for <n> entries`, run the check,
and report each entry with its hash, plus any left unresolved. Do not push.
