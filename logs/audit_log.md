# Audit log — decisions and discoveries

Append-only. Newest last. **Not read by default**: only when the history of a decision is actually
needed. `AGENT.md` holds the current state; this file holds *when* and *why*.

One entry per major decision or discovery:

```
## YYYY-MM-DD — <hash> — <title>
**Discovered / Decided:** what.
**Why:** the reasoning, including what was rejected.
**Cost:** what it broke, changed or left open.
```

**The entry is written after the commit it describes**, so the hash names the commit that actually
contains the work. An entry written before that commit exists says `uncommitted`, and the hash is
filled in once it does.

---

## 2026-11-09 — 767c183 — A Python package, not a shell script, not Rust

**Decided:** LabBrain is a Python package (`src/labbrain/`, standard library only at runtime), with
pixi and uv as its environments. The OKF tool `okf_vault.sh` was already about 1,100 lines of Python
in a 15-line `sh` wrapper. The wrapper existed only because the vault's `.gitignore` tracks `.sh` and
`.md` files, and that reason doesn't apply in a repo of its own.

**Why:**
- The heredoc can't be imported, linted, unit-tested or split into files, so nobody could
  contribute one function without editing a 1,100-line string.
- The lab's likely contributors (extraction, re-sweep, drift, indexing) work in Python and R.
- The work is file reads, `git` subprocesses and LLM calls taking seconds to minutes, so language
  speed buys nothing. The slow parts are algorithmic (one `git log` per file in `hot`).
- The LabWiki job sketches, open-llm's OpenAI-compatible API and a future MCP server are all
  Python-shaped.

**Rejected:**
- **Rust:** its one real advantage is a single binary with no environment, and `uv tool install`
  gets close. It would shut out the lab's contributors and mean rewriting 1,100 working lines from
  scratch.
- **Keeping the shell script:** none of the above becomes possible.

**Cost:**
- **The vault's `okf_vault.sh` and this package now exist side by side.** The vault keeps running
  its copy until it is replaced by a two-line shim, which is not done yet.
- **Nix was dropped.** pixi supplies Python and `git` instead.

## 2026-11-09 — 767c183 — Layout: skills seed, wikis evolve; patterns hold traces

**Decided:**
- **The vault's AGENT.md became skills.** The way it reads the vault became `search`, a read-only
  search skill. Its rules and commands became `okf-conventions`, `summary-writing`, `index` and
  `drift`. Each skill says why its job exists, when to run it, what code does and what the model
  writes, so any LLM can do the job by hand, and the nightly job follows the same steps.
- **`skills/` and `patterns/` here are seeds.** Each wiki evolves its own copies, and a good skill or
  pattern comes back by pull request.
- **`patterns/` holds the WikiSkills runtime traces.** Its README defines the formats, and
  `examples/` holds dummy traces. `logs/` holds this file.
- **Not ported, because they belong to one personal vault:** *recap* (a Kanban priority list),
  *commit* (`sync_vault.sh` across three repos), the IDS context, and the `.gitignore` and OneDrive
  gotchas.

**Why:** the user's decision. Raw traces contain a lab's data and must never reach a shared code repo.

**Cost:** `patterns/` is a draft format that nothing writes yet. Also, if a wiki keeps its skills
inside the vault, `labbrain check` will ask for an OKF `type` in each SKILL.md, which the SKILL.md
format doesn't have.

## 2026-11-09 — 767c183 — Parity tests before the split

**Decided:** The script moved, unchanged, to `tests/reference/okf_vault.sh`, and
`tests/test_parity.py` runs it next to the package on two copies of a dummy vault with git history.
It compares stdout, exit status and every file, with timestamps masked. There are 17 single
commands and one night-long sequence. The split into `labbrain.okf` was done mechanically, moving
each top-level definition verbatim with `ast` line spans, so the parity tests check the move rather
than a rewrite.

**Why:** the script is in daily use on a real vault, and no tests existed.

**Cost:**
- **The fixture has to reach each code path.** Planting two bugs showed it didn't at first: a
  wikilink with a heading and no alias was missing. `test_reference_sees_the_fixture` now names the
  paths it must reach.
- **On the real vault**, `check`, `stale` and `hot` gave byte-identical output from both.

## 2026-11-09 — 767c183 — Deliberate differences from okf_vault.sh

**Decided:**
- **Finding the vault:** from the working directory (the script's own location no longer means
  anything). The nearest folder with `.obsidian/` comes first; failing that, the nearest whose
  `index.md` declares `okf_version`. `.obsidian/` goes first because the personal vault's sub-repos
  are bundles of their own.
- **`frontmatter` needs `--by`:** the default `human:patrickCNMartin` was one person's name in a lab
  tool. A refusal is better than the wrong author written into every new note.
- **argparse:** argparse handles usage and help.
- **`history()` takes a cache made by its caller.** The module-level `_history` dictionary served
  history from before a commit to a second call in the same process. `tests/test_drift.py` showed
  1 change where there were 2.

**Why:** the first two are configuration that can't be one person's default. The third is a bug that
only appears once the code runs as a library, which is what the night run will do.

**Not done, deliberately:** `AGENT_TYPES`, `BOARD_TYPE` and `TEXT_EXT` stay as module constants,
although the plan listed them for configuration. No second wiki needs other values yet. The extra
types (Kanban, Daily Recap) and `.nix` are harmless in a wiki that doesn't have them. Configuration
waits until a second wiki asks for it.

## 2026-11-09 — 767c183 — Open: should `.gitignore` be an allowlist?

**Open:** the `.gitignore` is a denylist (a new file is tracked unless a rule says otherwise).
Patrick's note at the top of `.gitignore`:

> This could be a case where we want to have a blacklist all, then selectively whitelist. The
> reason is that it could lead to adding heavy files to the commit tree instead of just the wiki.
> Data should be tracked by DVC or lakeFS.

**Context for the decision:**
- **Two places it could apply:** this repo, which is code, skills and dummy fixtures; and the wikis
  LabBrain maintains, which hold the lab's notes beside its data.
- **The personal vault already works the other way:** its repos track only `.md`, `.sh` and `.nix`,
  and blacklist heavy files.
- **The current denylist** follows Hermetica. There, `detect-secrets` is the guard against leaked
  credentials, because it reads file contents. A denylist does nothing to stop large files.
- **Still to decide:** whether LabBrain's jobs should refuse to commit files over a size limit, or
  outside an allowed set of types, in a wiki, whichever way this repo's `.gitignore` goes.

## 2026-11-09 — 767c183 — Cleanup: task boards out, dead code out, paths checked

**Decided:**
- **Task boards are a separate feature.** The Obsidian Kanban plugin's format gets no special
  handling in the core any more:
  - `frontmatter` no longer types a `kanban-plugin` file as `Kanban Board`;
  - `check` no longer tests a board's links;
  - `hot` no longer watches boards.

  A board may come back later as a front-end feature. **Daily Recap** went too: it was in
  `AGENT_TYPES` and special-cased in `citations()`, for a *recap* command that was never ported.
- **Dead code removed:** `assemble()` stripped the pre-OKF keys `built:` and `folder:` from old
  summaries. None of the personal vault's summaries have them any more (grep: 0). Comments that
  pointed at the personal vault went with it.
- **A file argument outside the vault is refused,** and every argument is checked before any
  command writes anything. Until now `stamp` could write a file outside the wiki.
- **There is no `labbrain` pixi task.** pixi runs tasks from the repo root, so
  `pixi run labbrain stamp … Garden/x_summary.md` resolved the path against LabBrain, not the wiki.
  This was reproduced in a scratch folder. The skills now say
  `pixi run --manifest-path <LabBrain>/pixi.toml labbrain …` or `uv run --project <LabBrain> …`;
  both keep the working directory.

**Why:** the user's call on boards (an Obsidian plugin's format, and the wiki may not be run through
Obsidian). The path problem turned up while checking how the skills tell an agent to run labbrain.

**Cost:**
- **The personal vault, if it ever runs labbrain, loses board link checks and board hotness** until
  the feature exists. Its board keeps `type: Kanban Board`, which `check` still accepts.
- **The dummy vault changed.** `Board.md` is gone, and `Kitchen/Shopping.md` takes over its other
  job: a note with frontmatter but no `type`.

## 2026-11-09 — 767c183 — Settings in env/, and docs/

**Decided:**
- **`env/.env` holds settings about the person,** with a tracked `env/.env.example` in which every
  value is empty. There are two settings so far:
  - `LABBRAIN_CONTRIBUTOR`, the default for `frontmatter --by`. It must be `human:<name>`, with no
    email address;
  - `LABBRAIN_VAULT`, the wiki to use outside any wiki. It must be a wiki root.

  The real environment wins over the file, and `LABBRAIN_ENV` points at another file. An unknown
  `LABBRAIN_*` name in the file is refused, since it is usually a typo. Other names are ignored, so
  the file can be shared with other tools.
- **`python-dotenv` is the first runtime dependency.** A hand-written parser would be a few lines,
  but `.env` files carry quoting, `export` and comment rules that people already know from other
  tools, and a near-miss parser would read them differently.
- **The vault is the outermost folder whose `index.md` declares `okf_version`;** `.obsidian/` is no
  longer a marker. It still finds `~/Vaults` from inside `SciLifeLab_Vault`, because all three of
  the personal vault's bundle roots declare `okf_version`. `LABBRAIN_VAULT` comes after the wiki you
  are standing in, so an out-of-date value can't send writes to the wrong wiki.
- **A vault that isn't a folder is refused.** Before this, `check --vault /nonexistent` walked
  nothing and printed `OK: vault is OKF 0.2 conformant and current.`, and a stale `LABBRAIN_VAULT`
  would have done the same.
- **The model and preferences settings wait for `llm()`,** so `.env.example` never lists a setting
  that no code reads.
- **`docs/` holds how-to guides for people and agents:** how it works, functions and skills, writing
  each, usage and configuration. There are no per-function reference pages while the code moves.
- **`dev-skills/` holds skills for working on this repo,** starting with `update-docs`. They are kept
  apart from `skills/`, which wikis copy.
- **`tests/test_docs.py`** fails when `docs/usage.md` misses a command or option, when
  `.env.example` or `docs/configuration.md` misses a setting, or when a doc link leads nowhere.
  Planted errors of each kind were caught.

**Why:** the user asked for `env/` and the docs. The boundary (the person, not the wiki) and the
order (settings now, the model with `llm()`) were proposed earlier in the session. The contributor
check was added with the setting: the setting is the first place an actor comes from a file, and an
email address must never reach a note.

**Cost:**
- **The runtime is no longer standard library only.** Both locks now carry `python-dotenv` 1.2.4.
- **An installed wheel has no `env/.env`:** the path is the checkout's. Outside a checkout,
  `LABBRAIN_ENV` or the variables themselves are needed (a `ponytail:` comment in `cli.py`).
- **Found while documenting, not fixed:** `stamp` doesn't check that its argument is a folder
  summary, so given a raw note it rewrites the note's frontmatter as a summary's. This comes from
  `okf_vault.sh`, and `docs/usage.md` says so.

## 2026-11-09 — 767c183 — A note's text is untouchable; its header takes metadata with consent

**Decided:**
- **The rule is about a raw note's text, not its header.** Adding agent-readable metadata to the
  header doesn't change what the person wrote. That corrects the framing of the previous entry,
  which counted any header edit by `stamp` as a breach.
- **Consent is per author, recorded in each note:** `annotate: true` in the note's header.
  `frontmatter` writes it from the author's own `LABBRAIN_ANNOTATE` (in their `env/.env`) when it
  gives a new note its header. No setting, no settings file, or `false` means the key isn't written,
  and a note without it is never annotated.
- **Only into notes signed as the person whose setting it is** (`--by` equal to
  `LABBRAIN_CONTRIBUTOR`). Running `frontmatter --by human:ali` never writes your answer into Ali's
  notes. `LABBRAIN_ANNOTATE=true` without a contributor is refused, because it doesn't say whose
  notes it is about.
- **`generated` stays the author's; `annotated` records what agents add,** as a list of
  `{ by, at, keys }`, where an agent updates its own entry or adds one. The shape follows OKF v0.2's
  `verified` (a list of `{ by, at }`). `generated` couldn't hold several actors: OKF defines its `by`
  as one actor, "how the current content was produced". OKF lets producers add keys, and readers must
  keep keys they don't know.
- **`stamp` refuses a file that isn't a folder summary** (the one `stale` watches in its folder),
  before writing anything. Given a note, it replaced the author in `generated` with the actor and
  added the folder's `sources` and `children`: false metadata, whoever it names.

**Why:** the user doesn't want agents adding to their notes; others might. The person running a job
is often not the note's author (a nightly job, a colleague), so the runner's settings can't decide.
Rejected along the way: a list of consenting authors in a wiki-wide file (option A), and a key the
author writes by hand in each note (option B). The user chose C: the key in the note, filled from
the author's own settings.

**Cost:**
- **Existing notes have no key, so they are never annotated** until their author adds
  `annotate: true` by hand. A change of mind doesn't reach notes that already have a header.
- **Nothing writes `annotated` yet.** The rule is in AGENT.md and `okf-conventions`; the command that
  writes agent metadata (code writes the key and the entry, the model only the value) comes with the
  first job that needs it.
- **`stamp` differs from `okf_vault.sh`** on a non-summary argument; the parity cases never pass one.

## 2026-11-09 — 0ed7507 — CI on GitHub, and the pre-push hook for both tools

**Decided:**
- **`.github/workflows/ci.yml` runs on every push to `main` and every pull request.**
  - **pixi:** the tests on Python 3.13 (`dev`) and 3.11 (`py311`), then the pre-push hook's checks
    (ruff, detect-secrets) for anyone who didn't install the hook.
  - **uv:** the tests on 3.11 and 3.13.
  - Each job installs with its lock enforced, so a stale `pixi.lock` or `uv.lock` fails the run.
- **Both tools are tested** because both are supported ways to install LabBrain, and each resolves
  from its own lock and its own package source (conda-forge or PyPI).
- **Hardening:** actions pinned to a commit hash (`actions/checkout` v7.0.1, `prefix-dev/setup-pixi`
  v0.11.3, `astral-sh/setup-uv` v10.3.3), a read-only token, `persist-credentials: false`, and the
  `pull_request` trigger, so a fork's code never runs with write access or secrets. pixi 0.83.0 and
  uv 0.13.7 are pinned to the versions the locks were made with.
- **Linux only.** Development happens on macOS, and the tests run there before a push; a macOS job
  can be added if a platform-specific bug turns up.
- **The pre-push hook works with either tool.** It records the Python it was installed with (pixi's
  `dev` environment, or uv's `.venv`), and the checks run in pre-commit's own environments, pinned
  by `rev`. Both were installed in a scratch copy and fired by a real `git push`.

**Why:** the user asked for CI on pushes to `main` and on pull requests, and whether the hook
works with pixi and uv.

**Cost:**
- **Not yet run on GitHub.** actionlint passes, and the uv job's steps pass locally on 3.11 and
  3.13, but the Linux runs are unverified: Docker wasn't running to try them first.
- **The pre-commit environments aren't cached in CI,** so the checks download ruff and
  detect-secrets on each run, which takes a few seconds.

## 2026-11-09 — ff80dae — The personal vault runs labbrain; its okf_vault.sh is deleted

**Decided:** The personal vault no longer has `okf_vault.sh`. It runs `labbrain` instead, and reads
LabBrain's base skills in place rather than copying them. Its own skills are in the vault's
`skills/`: *recap* (a daily recap of the Kanban board's priorities), *kanban* (the board) and
*commit* (`sync_vault.sh` across its three repos). Its settings are in the vault's own `env/.env`,
read through `LABBRAIN_ENV`. It runs a local `vaults` branch, checked out as a separate worktree, so
work on `main` doesn't reach it until its author merges `main` into `vaults` by hand.

This settles the cost noted in the first entry: the script and the package no longer run side by
side, and no shim was needed. `tests/reference/okf_vault.sh` is now the only copy of the script,
and stays the parity contract.

**Why:** the user's decision. Before the switch, both were run on the vault:
- `check` and `stale` printed the same output;
- `hot` differed only in no longer listing the task board;
- `frontmatter`, `links`, `index` and `stamp` left identical copies of the vault.

**Cost:**
- **Board handling stays out of LabBrain,** because it is an Obsidian plugin's format. The vault's
  *kanban* skill does it instead. It reads broken board links from the `unresolved` lines of
  `labbrain links`, decides which summaries are due a drift check against the board with git, and
  records each check with `labbrain drift-stamp`, naming the summaries.
- **That due rule is half of `hot`'s:** it counts changes to the board, not edits to the summary.
- **A fix on `main` reaches the vault only once it is merged into `vaults`.**

## 2026-11-09 — ff80dae — links removes an emptied drift_verification key

**Discovered:** When `links` dropped a summary's last drift record, because the checked file was
deleted or moved, it left `drift_verification:` with nothing under it: `drift_lines([])` still
returns the key's line. `okf_vault.sh` does the same. It showed in the personal vault when its
`okf_vault.sh` was deleted, since a summary's only record was a check against that script.

**Decided:**
- `carry_hashes` passes no lines once the list is empty, and `assemble` then removes the key.
- `test_links_removes_an_emptied_drift_key` runs both on the dummy vault and expects this to be the
  only difference.
- AGENT.md lists the change among the known differences, and `docs/usage.md` describes it.

**Why:** an empty key reads as "never checked", so nothing broke, but it was noise in the
frontmatter, and it stayed until the next `drift-stamp`. No parity case reached it: the dummy vault
never deleted a file that had a drift record.

**Cost:** a key left empty before the fix stays until the next `drift-stamp` refills it, because
`links` rewrites a summary only when its records change. The personal vault's one case was removed
by hand.
