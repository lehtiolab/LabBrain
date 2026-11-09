---
name: update-docs
description: Bring LabBrain's own documentation back in line with its code - the README, docs/, env/.env.example, the skills' command tables and AGENT.md's list of differences. Use once a change to a command, option, default, output, exit status, setting or the repo's layout has settled, before a release, or when asked to update or check the docs. Tests find what is missing; the model checks that what the docs say is what the code does.
---

# update-docs: keep LabBrain's docs true to its code

This skill is for working on the LabBrain repo, not on a wiki.

## Why
People and agents follow the docs, not the code. A wrong doc does more harm than a missing one: a
skill that told agents to run `pixi run labbrain` once sent their file paths to the wrong folder.
Docs drift whenever the code changes and nobody goes back to them.

## When
- **Once a change has settled:** a command, option, default, output, exit status or setting, or the
  repo's layout. Not halfway through a change: docs written for code that is still moving are stale
  before anyone reads them.
- **Before a release,** or when asked.

If `tests/test_docs.py` passes and `git log` shows no change to the code since the docs were last
updated, there is nothing to do: say so and stop.

## Code versus model
| step | done by |
|---|---|
| a command, option or setting the docs don't mention | code: `tests/test_docs.py` |
| a link in the docs to a file that doesn't exist | code: `tests/test_docs.py` |
| a command named in a skill that doesn't exist | code: `tests/test_skills.py` |
| whether the docs say what the code does | **the model** |
| the examples | **the model**, copied from real output |

## Where each fact is written
The code is the source, and the docs follow it. When one of these changes, update every file listed.

| fact | source | written in |
|---|---|---|
| the commands, and what each does | `COMMANDS` in `cli.py` | `README.md` (Commands), `docs/usage.md`, `skills/okf-conventions/SKILL.md` (Commands) |
| options, defaults, output, exit status | `parser()` and `main()` in `cli.py` | `docs/usage.md` |
| how to run labbrain from a wiki | `pixi.toml` | `README.md`, `docs/usage.md`, the *Running labbrain* section of each skill in `skills/`, word for word the same in each |
| the settings | `SETTINGS` and `settings()` in `cli.py` | `env/.env.example`, `docs/configuration.md` |
| how the package differs from `okf_vault.sh` | `tests/test_parity.py`, `tests/test_cli.py` | `AGENT.md` (known differences) |
| the repo's layout | the folders | `README.md` (Layout), `docs/how-it-works.md`, `AGENT.md` (What LabBrain is) |
| the skills | `skills/` | `README.md` (Skills), `docs/how-it-works.md` |
| the modules | `src/labbrain/okf/` | `docs/writing-a-function.md` (Where it goes) |
| the checks before a push, and in CI | `.pre-commit-config.yaml`, `.github/workflows/ci.yml` | `README.md` (Contributing), `docs/writing-a-function.md` (Before you push), `AGENT.md` (Conventions) |
| the rules for contributors | `AGENT.md` | `docs/writing-a-function.md`, `docs/writing-a-skill.md`, `README.md` (Contributing) |

AGENT.md holds the rules, and the docs explain them. When a doc and AGENT.md disagree, fix the doc,
unless the code agrees with the doc: then it is a question for a person (see *Stop and ask*).

## Steps
1. **Find what changed** since the docs were last updated: `git log` and `git diff` over `src/`,
   `skills/`, `env/`, `pyproject.toml` and `pixi.toml`.
2. **Run the doc tests:** `pixi run -e dev pytest tests/test_docs.py tests/test_skills.py`. Each
   failure names a missing command, option, setting or link.
3. **Read the code path of each change,** not only the diff: the parser, the branch in `main()`, and
   the function it calls.
4. **Run it.** Copy `tests/fixtures/vault/` to a scratch folder, `git init` and commit it, run the
   command there, and take the examples from its real output. Never run a command that writes on a
   real wiki to get an example.
5. **Update every file** the table lists for that fact. Plain language, one point per line, and a
   link to another doc rather than a copy of it.
6. **Check:** `pixi run -e dev test` and `pixi run -e dev lint`.
7. **Report** what you changed, what you checked by running it, and anything still open.

## Rules
- **Describe what the code does today.** Mark what is planned as planned, or leave it out.
- **No reference pages for individual functions** yet: the docstrings are the reference while the
  code moves.
- **AGENT.md stays lean:** a rule there is one or two lines, and the explanation goes in `docs/`.
- **The audit log is for decisions.** Docs catching up with the code is not one.

## Stop and ask
Stop, and don't edit, when:
- **the code does something a doc or AGENT.md says it shouldn't.** It may be a bug: report it, rather
  than document the bug as intended;
- **documenting a change would change a rule in AGENT.md;**
- **it's unclear who a doc is for.**

Say what you found, the options and the one you recommend, then wait for an answer.
