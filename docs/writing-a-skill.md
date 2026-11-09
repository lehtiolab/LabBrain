# Writing a skill

How to add to, or change, the skills that LLMs follow when they work on a wiki.

## When a skill is the right tool
Write a skill for a job, or part of one, that needs a note read: writing, comparing, judging,
answering. If every step can be worked out by code, write a function instead
(see [Functions and skills](functions-and-skills.md)). Before you start a new skill, check whether
an existing one should simply gain a step.

## The format
A skill is `skills/<name>/SKILL.md`:
```markdown
---
name: drift
description: Check that folder summaries still say what their notes say, starting with the notes that change most (a drift scan). Use when asked to scan, check for drift or verify summaries, after the index skill has run. …
---

# drift: check summaries against the notes that change most
…
```
- **`name`** is the folder's name: lowercase letters, digits and hyphens.
- **`description`** is at most 1024 characters. An agent sees only this when it decides whether to
  load the skill, so say what the skill does and when to use it, in the words people use when they
  ask for it ("scan", "check for drift").

This is the `SKILL.md` format that Claude Code and other agent tools load on their own. You can also
paste a skill into any chat.

## The sections
The job skills (`index`, `drift`, `summary-writing`) keep the same order, so a model knows where to
look:

| section | says |
|---|---|
| Why | what goes wrong without this job |
| When | when to run it, and how to tell there's nothing to do, so the model stops early |
| Code versus model | a table of the steps, and whether a `labbrain` command or the model does each |
| Steps | numbered, one action each, with the exact command for each code step |
| Rules | what the model must never do (only if the job has such rules) |
| Stop and ask | when the model stops and waits for a person |
| Running labbrain | how to run the command from a wiki; copy it from an existing skill |

A reference skill (`okf-conventions`) and a read-only skill (`search`) arrange their own sections,
but still say at the top what they are for.

## Writing it
- **Write for any LLM, including a small one.** Plain words, short sentences, one instruction per
  line, and nothing that only one tool understands.
- **Say why.** A model follows a rule more sensibly when it knows the reason.
- **Never ask the model to do what a command does.** Hashes, lists of files, dates, paths and
  listings come from `labbrain`. Name the command: `labbrain stamp --by <your actor> <summary>`.
- **Write commands in backticks,** as `labbrain <command>`. `tests/test_skills.py` fails on a command
  that doesn't exist, so a renamed command can't leave a skill behind.
- **Say which files the model may write,** and that a raw note's text stays as its author wrote it.
  Its header changes only through `labbrain` commands.
- **Make stopping explicit.** List the cases where the model must stop and ask, and what it should
  report: what it found, the options, and the one it recommends. A question buried at the end of a
  long run never gets seen.
- **Point to another skill rather than copy it.** `okf-conventions` holds the wiki's rules, and
  `summary-writing` holds how to write a summary.
- **Cheapest first.** Have the model read listings and summaries before raw notes, and stop as soon
  as there is nothing to do.

## Testing it
1. **The form:** `pixi run -e dev test` runs `tests/test_skills.py`, which checks the frontmatter and
   the commands.
2. **On a copy, never on a real wiki first.** Copy `tests/fixtures/vault/` to a scratch folder, run
   `git init`, and commit everything. Start a fresh session of your LLM in that folder, load the
   skill, and ask for the job. Then check:
   - did it run the commands, rather than write hashes or listings itself?
   - did it stop and ask where the skill says to?
   - did it change only the files it may?
3. **On a real wiki,** start with the read-only commands.

## Skills in a wiki
The skills here are seeds. A wiki copies them into its own `skills/`, and they evolve there. Each run
will leave a trace that names the version of the skill it followed (the git blob hash of its
`SKILL.md`), so a change in results can be traced to a change in the skill or in the model.

When a wiki's copy works better in a way that isn't particular to that lab, bring it back here by
pull request, with the lab's data taken out.

A change to a skill changes what agents write as much as a change to the code does, so review it
like code.

## Skills for working on this repo
The skills in `skills/` are for agents working on a wiki. Skills for developing LabBrain itself
(today only `update-docs`) live in `dev-skills/`, so that a wiki copying `skills/` doesn't pick them
up. They use the same format and the same tests.
