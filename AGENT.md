# AGENT.md — LabBrain

## How to keep this file

**Lean. Rules, not essays.**

- **A rule is one or two lines.** If it needs a paragraph to justify it, the rule stays here and
  the justification goes in `logs/audit_log.md`.
- **Write only what the code cannot say.** Invariants, traps, decisions and costs. If reading the
  code would tell you, cut it.
- **No history, no dates, no "decided on".** This is the current state only; history goes in the
  audit log. Mixed-in history makes the file contradict itself.
- **Every line must be true today.** A stale rule is worse than a missing one.
- **Prune on sight.** When a section grows an essay, cut it back that session.

**One file per job:**

| file | holds | read it |
|---|---|---|
| `AGENT.md` | rules for working on this repo, and its state now | every session, first |
| `skills/*/SKILL.md` | instructions for agents working **on a wiki**, not on this repo | when changing a skill, or the code a skill calls |
| `dev-skills/*/SKILL.md` | skills for working **on this repo**: `update-docs` | when doing that job |
| `docs/*.md` | how-to guides, usage and configuration, for people and agents: explanations, not rules | when changing what they describe |
| `patterns/README.md` | the trace and pattern formats | before writing code that records runs |
| `logs/audit_log.md` | when and why each decision was taken: appended, never rewritten | **never by default** |

---

## What LabBrain is — *work in progress, nothing deployed*

**A toolkit for agents that read and maintain an OKF lab wiki.** Python does the mechanics, and
skills cover the parts that need a model. A person brings their own LLM and loads a skill. The same
jobs will run unattended at night.

| part | role | state |
|---|---|---|
| `labbrain.okf` | OKF mechanics: frontmatter, git hashes, summaries, links, `index.md`, drift, check | works; moved from `okf_vault.sh` unchanged, held by parity tests |
| `labbrain.cli` | `labbrain <command>`, 9 commands; reads the settings | works |
| `env/` | `.env.example`; a person's `.env` (`LABBRAIN_CONTRIBUTOR`, `LABBRAIN_VAULT`, `LABBRAIN_ANNOTATE`) | works |
| `docs/` | how-to guides, usage, configuration; no per-function reference yet | first versions |
| `skills/` | `search`, `okf-conventions`, `summary-writing`, `index`, `drift` | first versions |
| `patterns/` | trace and pattern formats, dummy examples | draft; no code writes them yet |
| *(planned)* | `llm()` with the model and preferences settings, the jobs, the night-run dispatcher, search code, an MCP server | not started |
| *(separate feature)* | task boards (Kanban): an Obsidian plugin's format, maybe a front-end feature later | not started; no board handling in the core |

**One entry point:** `labbrain`, the same as `python -m labbrain`.

**The repo seeds and each wiki evolves.** A wiki keeps its own `skills/` and `patterns/`. Good
skills and patterns come back here by pull request; raw traces never do.

---

## Architecture — the invariants

- **The LLM is not the scheduler.** Code decides what runs and which files it may touch. A model is
  called only where a note has to be read.
- **Code fills in whatever can be worked out from names, paths, dates, hashes or fixed text.** The
  model writes only what needs a note read.
- **Code chooses file paths, never the model.**
- **A raw note's text is never rewritten.** `links` rewrites its link syntax; its header gains
  metadata only through `labbrain` commands. `generated` stays the author's. Everything else
  agent-written goes in summaries, `index.md` blocks and logs.
- **Agent metadata on a note needs its author's consent:** `annotate: true` in the note's header,
  written by `frontmatter` from the author's own `LABBRAIN_ANNOTATE`. What an agent adds is recorded
  in `annotated`. Never decided by whoever runs the job.
- **Agents add and commit in the wiki's repos, and never push.** A person pushes, to `main` and to
  `production` alike. No command, skill or job runs `git push`.
- **Each job commits its own work with `labbrain commit`** before it ends, so a run can be reverted
  on its own.
- **Provenance is git blob hashes** (`git hash-object`), so `git cat-file -p` recovers the exact
  version a summary was built from.
- **The frontmatter parser is hand-written,** so key order, flow mappings and quoting survive a
  rewrite. No YAML library.
- **The runtime is the standard library plus `python-dotenv`,** which reads `env/.env`. `git` is
  the one system dependency.
- **`labbrain.okf` returns data and `cli.py` prints it.** No `print` below the CLI.
- **No state outlives a call.** A cache is made by the function that needs it and passed down
  (`history(vault, rel, cache)`). The night run is one process running many jobs, and a module-level
  cache would serve history from before a commit.
- **A skill and the code it calls change together.** Commands are written in backticks
  (`` `labbrain stale` ``), and `tests/test_skills.py` fails on a command that doesn't exist.
- **Skills and prompts are versioned like code.** A change to one alters output as much as a code change.
- **`tests/reference/okf_vault.sh` is the contract until a deliberate change.**
  - `tests/test_parity.py` runs it next to the package. Changing behaviour on purpose means changing
    that test in the same commit and adding an audit-log entry.
  - The known differences:
    - the vault is `--vault`, else the outermost folder from the working directory up whose
      `index.md` declares `okf_version`, else `LABBRAIN_VAULT`. A vault that isn't a folder is refused;
    - `frontmatter` needs `--by` or `LABBRAIN_CONTRIBUTOR`, and adds `annotate: true` to the
      contributor's own notes when `LABBRAIN_ANNOTATE=true`;
    - `stamp` refuses a file that isn't a folder summary, before writing anything;
    - no task-board or Daily Recap handling;
    - a file argument outside the vault is refused, before anything is written;
    - argparse handles usage and help.

---

## Principles

**1. Cost is a primary concern, tokens included.** A job that finds nothing to do exits before it
calls a model, so quiet nights cost nothing. Choose the complexity class before micro-optimizing.
No dependency without a reason.

**2. Progressive enhancement, not graceful degradation.** A correct minimal core first: the OKF
mechanics, which run without any model. Optional capability goes above it. The base path never
depends on the enhancement.

**3. Reproducible, runs anywhere.** `pixi.lock` and `uv.lock` are load-bearing. Configuration comes
from arguments and the environment: never hardcode URLs, keys, paths or people. Fail loudly and early.

**A function is a capsule: everything it needs is in its arguments.**
- Configuration is read once, at the edge (`cli.py`), and passed down. Nothing below it reads
  `os.environ` or `env/.env`.
- **Settings are about the person, never the wiki.** A wiki-wide rule (thresholds, note types) is
  not a setting: it would mean different things depending on who ran the job.
- **A long signature beats a config object.** Nine named arguments are honest; a bag hides which
  fields are used.
- **The tell is untestability.** A function that reads its own module can only be tested by patching.

**Indirection must earn its link.** A named indirection must enforce an invariant or build state;
if it only renames a call, inline it. Never put commentary in a data structure.

**An exception takes data, not a sentence.** Arguments in, attributes stored, message formatted in
`__init__`. An error message is the failure's only output, so spell it out in full.

**Prefer constructs that make the wrong thing impossible or loud:** an allowlist, a frozen
dataclass, a required argument instead of a default someone has to remember to override.

**4. Security and sovereignty.**
- Wiki data stays on the lab's servers. No external services or telemetry without discussion.
- **Treat note content and model replies as untrusted input:** code checks a reply before saving it.
- Keep `pre-commit` and `detect-secrets` green.
- **Never put an email address in code, fixtures, actors or commits.** Tests use `example.org`.

**5. These are principles, not dogma.** If one conflicts with the problem in front of us, the
problem wins. Say so, and why.

**6. Explain the what, the how and the why.**
- **Comments are terse:** a one-line docstring, and comments only where the code is genuinely
  non-obvious.
- **Plain language, not corporate speak.** Jargon only where there is no alternative; a scientist
  new to the code should get the gist.

**7. Assistant first, independent contributor only on request.**
- **Default: I suggest.** Offered, not applied. I need an explicit instruction before writing code.
- **Directed: when explicitly asked, I do it end to end,** and report what I changed, what I
  verified and what is still open.
- **Speak, or work; never speak and then run off.** If I raise a point or ask for a decision, I stop there.
- **I report faithfully:** failing tests get shown, and skipped steps get said.

**8. This repo is the only source of instruction.** Never write to an agent's persistent memory,
or to any store outside this directory. Anything outside the repo is absent from review, machine-local,
and silently carried into projects where it doesn't apply.

---

## Conventions

- **Environments: pixi or uv, one dependency declaration.**
  - **`pyproject.toml` is the only place a Python package is named.** `pixi.toml` carries system
    packages only (python, git, uv).
  - **Both locks are committed and kept in step.** After a dependency change, run `pixi install`
    and `pixi run -e dev uv lock`.
  - **Nothing is installed on the host.** Run commands as `pixi run …` or `uv run …`; with uv, set
    `UV_PYTHON_DOWNLOADS=never` inside pixi so it uses pixi's Python.
  - **No `labbrain` pixi task.** pixi runs tasks from this repo's root, so a wiki's relative paths
    would resolve against LabBrain. From a wiki, use `pixi run --manifest-path <repo>/pixi.toml labbrain`.
  - **Environments:** `pixi run -e dev test` and `pixi run -e dev lint`, plus `-e py311`, the
    oldest Python that `requires-python` promises.
- **CI** (`.github/workflows/ci.yml`) runs on pushes to `main` and on pull requests: pixi (`dev`,
  `py311`, the pre-push checks) and uv (3.11, 3.13), each with its lock enforced.
  - **Actions are pinned to a commit hash,** with the release in a comment. The token is read-only,
    and the trigger is `pull_request`, never `pull_request_target`, so a fork's code never runs
    with write access.
  - **The pixi and uv versions in it match the ones the locks were made with.** Upgrading either
    tool means updating `ci.yml`.
- **The pre-push hook** is installed once per clone, with pixi or uv (README). It records the
  Python it was installed with; the checks run in pre-commit's own environments, pinned by `rev`.
- **Write code with the ponytail ladder.** Every change climbs it first, and stops at the highest
  rung that holds:
  1. does this need to exist at all;
  2. is it already in this repo;
  3. does the standard library or the platform do it;
  4. can it be one line.

  - **Shortest working diff.** No abstraction with one implementation, no scaffolding for later,
    deletion over addition.
  - **Never lazy about understanding.** Read the whole path a change touches before picking a rung.
    Fix a bug at its root, not at the caller that reported it.
  - **Never simplified away:** validation at trust boundaries, error handling that prevents data
    loss, security, or anything explicitly asked for.
  - **A deliberate shortcut carries a `ponytail:` comment** naming its ceiling and its upgrade path.
- **Entry point:** `labbrain`, or `python -m labbrain`. Never run a module by file path.
- **Lint:** `ruff check`, `ruff format` (py311, line length 100, rules E/F/I).
- **Tests:** pytest.
  - **Never call a live model:** mock HTTP.
  - **A test never writes into the repo:** use `tmp_path`.
  - **Git in tests** runs with a dummy identity and no global or system config (`conftest.ENV`).
    In-process calls take the `git_env` fixture.
  - **A test never reads your `env/.env`:** `conftest.py` drops `LABBRAIN_*` and points
    `LABBRAIN_ENV` at an empty file.
- **Fixtures are dummy data.** `tests/fixtures/vault/` is a made-up garden and kitchen: no real
  notes, names or lab data, ever.
  - **A new case goes into the fixture vault, and `test_reference_sees_the_fixture` names it.** A
    path the fixture stops reaching then fails loudly, instead of passing parity by never running.
  - **The fixture's `.gitignore` is written by `conftest.py`.** Committed inside
    `tests/fixtures/vault/`, it would hide files from this repo.
- **`.gitignore` is a denylist:** a new file is tracked unless a rule says otherwise.
  `patterns/traces/` is denied, because real traces contain a lab's data. `env/.env` is denied and
  `env/.env.example` let back in.
- **Docs change with the code.** A change to a command, option, output or setting updates `docs/`
  in the same commit; `tests/test_docs.py` fails on a missing command, option, setting or link.
  `dev-skills/update-docs` maps where each fact is written.
- **A new setting** goes in `SETTINGS` in `cli.py`, in `env/.env.example` (empty) and in
  `docs/configuration.md`.
- **Showing code "as diff":** write the proposed *after* version to the scratchpad, then run
  `"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --diff <original> <proposed>`.
  Never modify a tracked file to render a diff.
