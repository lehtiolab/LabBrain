---
name: logging
description: Record a decision taken in an agent session as a new file of its own in LabBrain's logs/decisions/, committed together with the work it describes and holding no hash, and print the audit log with each record's hash looked up from git. Use when asked to log a decision, and when a major decision or discovery has been made in a session. A decision a person takes without an agent goes in the pull request instead. Commits locally; never pushes.
---

# logging: one file per decision, committed with its work

This skill is for working on the LabBrain repo. Each decision is a file of its own in `logs/decisions/`.
`logs/audit_log.md` is the log from before records, frozen. `sh dev-skills/logging/log.sh` prints the whole log.

## Why
Several people and agents log decisions, each on their own branch. Entries appended to one file
conflict on every merge, because every branch writes at its end, and a hash written into an entry
needs a second commit and a later edit. So each decision is a new file, which no other branch
writes, and it holds no hash: git knows which commit added it, and `log.sh` looks that up each time
the log is read. The record goes in the same commit as its work, so that commit holds both. Nothing
stored depends on a hash, so a rebase or a squash merge leaves the log right.

## What goes in it
- **Decisions and discoveries from an agent session** that shape the code: taken by the agent, or
  agreed between the agent and the person it works with.
- **Not a decision a person takes on their own.** That goes in the pull request description.
- **Not routine work:** docs catching up with the code, a fixed typo, a test for what already works.

## Rules
- **Never push.** Not after a commit, not to finish the job, not when asked to log. Pushing is the
  user's.
- **Never commit on `main`.** Work reaches `main` only by pull request from a `feat/` branch. If
  `git branch --show-current` says `main`, stop and ask which `feat/<topic>` branch to use, then
  `git switch -c feat/<topic>`; uncommitted work comes with it.
- **Never edit `logs/audit_log.md`.** It is the history from before records, kept as it was.
- **One decision, one record,** at `logs/decisions/YYYY-MM-DD-<topic>.md`: the date, then a few lowercase
  words joined by hyphens that name the decision. Never a running number: two branches would both
  take the next one. The name must be new on every branch: `git log --all --oneline -- <path>`
  prints nothing.
- **No hash in a record.** `log.sh` looks it up.
- **The record goes in the same commit as its work.** A decision that changed no file is a commit
  holding only its record. Never commit a record without its work.
- **Commit only what the decision touched.** Stage named paths, `git add -- <path>…`; never
  `git add -A`, `git add .` or `git commit -a`. Unrelated changes stay unstaged. If one file holds
  both, ask before staging it.
- **Never `--no-verify`.** A failing hook stops the commit; report it, and the record stays
  uncommitted.
- **A committed record is not rewritten.** A typo or a wrong fact is fixed in place. A decision
  that changes, or is reversed, is a new record whose `supersedes` names the old record's file.
- **Never rename, move or delete a record.** Its hash is the commit that added it at that path; a
  renamed record would take the hash of the rename.
- **Never commit the printed log.** It is made each time it is read, so it never conflicts.
- AGENT.md's rules on commits still hold: read `git status` first; no data, secrets or generated
  files.

## Record format
```
---
date: YYYY-MM-DD
title: <title>
decided_by: [human:<handle>, <tool>/<model>]
supersedes: <YYYY-MM-DD-topic>.md
---

**Discovered / Decided:** what.
**Why:** the reasoning, including what was rejected.
**Cost:** what it broke, changed or left open.
```
- **`decided_by`** names who took the decision, as actors: the person as `human:<handle>` (their `LABBRAIN_CONTRIBUTOR`, if set; otherwise ask),
  and you as `<tool>/<model>`, e.g. `claude-code/claude-opus-5-5`. A decision you took alone names
  only you. **Never an email address.**
- **`supersedes`** only when the record replaces an earlier one; otherwise leave the line out.
- **Put the title in double quotes** if it holds a colon.

## Logging a decision
When asked to log a decision, being asked is the go-ahead to commit it.
1. `git status` and `git diff`: list the paths that belong to the decision.
2. Name the record, and check the name is new: `git log --all --oneline -- logs/decisions/<name>.md`
   prints nothing.
3. Write the record.
4. Commit work and record together: `git add -- <paths> logs/decisions/<name>.md`, then
   `git commit -m "<title>"`.
5. Run `sh dev-skills/logging/log.sh --uncommitted`: the record is not listed.
6. Report the hash (`git log -1 --format=%h`) and anything left unstaged. Do not push.

If the work can't be committed yet (the user says not yet, the tests fail, a hook refuses), write
the record and stop. It stays uncommitted, `git status` shows it, and it goes in with the work when
that is committed. If the work was committed before it was logged, commit the record on its own and
name the work's commit in its body; that hash is plain text, and nothing checks it.

## Reading the log
`sh dev-skills/logging/log.sh` prints `logs/audit_log.md`, then every record oldest first under a `## YYYY-MM-DD — <hash> — <title>`
header. The hash is the commit that added the record, or `uncommitted`. It needs the full history:
a shallow clone shows older records with the wrong hash.

`sh dev-skills/logging/log.sh --uncommitted` lists the records not yet committed, or edited since: exit 0 none, 1 some, 2
it could not check.
