# LabBrain

Tools and skills for agents that read and maintain a lab wiki written in the
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2). *Work in progress; nothing is deployed yet.*

The split is simple:
- **code does what can be worked out** from file names, paths, dates and git hashes: headers,
  provenance, `index.md` listings, staleness and drift bookkeeping;
- **a model is called only where a note has to be read:** writing summaries, comparing what they say.

You can bring your own LLM, load a skill, and do a job by hand. The same jobs are meant to run
unattended at night.

## Functions and skills
LabBrain is made of two kinds of thing, and most jobs need both.

| | function | skill |
|---|---|---|
| is | Python, in `src/labbrain/okf/` | markdown, in `skills/<name>/SKILL.md` |
| run by | the computer, through `labbrain <command>` | an LLM, which reads it and follows it |
| does | what can be worked out from names, paths, dates, git hashes or fixed text | what needs a note read: writing, comparing, judging |
| gives | the same answer every time | an answer that varies with the model, and needs checking |
| costs | nothing | tokens |
| example | `labbrain stale` lists the summaries whose notes changed | `summary-writing` says how to rebuild one faithfully |

A skill tells the model which commands to run, and the commands do the mechanical part: the model
never writes a hash, a file list or a listing by hand. See
[docs/functions-and-skills.md](docs/functions-and-skills.md) for how to tell which one a job needs.

## Install

With [pixi](https://pixi.sh), which also brings Python and git:
```sh
pixi install
pixi run labbrain --help
```

With [uv](https://docs.astral.sh/uv/), if you already have Python ≥ 3.11 and git:
```sh
uv sync
uv run labbrain --help
```

Optionally, put your name and your usual wiki in `env/.env`, so you don't have to pass them each
time (see [docs/configuration.md](docs/configuration.md)):
```sh
cp env/.env.example env/.env
```

## Commands
Run them from the wiki root, or anywhere with `--vault <wiki root>`. File arguments are relative to
where you run the command, and must be inside the wiki. To use a LabBrain checkout without leaving
the wiki, run `pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`. Every option, output and exit status is in
[docs/usage.md](docs/usage.md).

| command | what it does |
|---|---|
| `labbrain check` | everything below; exits with 1 if anything is off |
| `labbrain stale` | summaries whose notes changed since they were built, and why |
| `labbrain stamp --by ACTOR SUMMARY...` | after rebuilding a summary: its sources, git hashes, parent, children and time |
| `labbrain index` | regenerates every `index.md` listing |
| `labbrain frontmatter [--by ACTOR]` | gives new notes their minimal OKF header; the author defaults to `LABBRAIN_CONTRIBUTOR` |
| `labbrain links [FILE...]` | turns `[[wikilinks]]` into relative markdown links |
| `labbrain hot` | often-changed files, the files that cite them, and which are due a drift check |
| `labbrain drift-stamp --by ACTOR FILE [SUMMARY...]` | records a drift check |

## Skills
Instructions for an agent working on a wiki, in the `SKILL.md` format. Load the ones a job needs.

| skill | for |
|---|---|
| [search](skills/search/SKILL.md) | finding things and answering questions; read-only |
| [okf-conventions](skills/okf-conventions/SKILL.md) | the rules the wiki follows; a reference for the other skills |
| [summary-writing](skills/summary-writing/SKILL.md) | writing and rebuilding a folder summary faithfully |
| [index](skills/index/SKILL.md) | bringing headers, summaries, listings and the map up to date |
| [drift](skills/drift/SKILL.md) | checking that summaries still say what their notes say |

The skills here are seeds. Each wiki keeps and evolves its own copies, and what it learns from its
runs goes in its `patterns/` (see [patterns/README.md](patterns/README.md)). A skill or pattern that
works beyond one lab comes back here by pull request. Raw traces never do.

## Docs
How-to guides for people and agents are in [docs/](docs/README.md): how LabBrain works, functions and
skills, writing each of them, usage and configuration.

## Layout
```
src/labbrain/cli.py     the labbrain command; reads the settings
src/labbrain/okf/       OKF mechanics: files, frontmatter, git, summaries, notes, links, index, drift, check
skills/                 seed skills, for agents working on a wiki
dev-skills/             skills for agents working on this repo
patterns/               trace and pattern formats, with dummy examples
docs/                   how-to guides, usage and configuration
env/                    .env.example; your own .env, which git ignores
logs/audit_log.md       when and why each decision was taken
tests/                  pytest; reference/ holds okf_vault.sh, which the parity tests compare against
```

## Contributing
Read [AGENT.md](AGENT.md) first: it holds the rules for this repo, for people and coding agents alike.

- **A function:** goes in the `labbrain.okf` module it belongs to, takes everything it needs as
  arguments, and comes with a test. It never prints; `cli.py` does that. See
  [docs/writing-a-function.md](docs/writing-a-function.md).
- **A skill:** `skills/<name>/SKILL.md`, with `name` (the folder name) and `description` in its
  frontmatter. Write commands in backticks (`` `labbrain stale` ``); `tests/test_skills.py` checks
  they exist. See [docs/writing-a-skill.md](docs/writing-a-skill.md).
- **A change to a command, option or setting** updates the docs in the same commit;
  `tests/test_docs.py` fails on a missing one.
- **Before pushing:**
  ```sh
  pixi run -e dev test
  pixi run -e py311 test
  pixi run -e dev lint
  ```
  To have the lint and secret checks run before every push, also run
  `pixi run -e dev pre-commit install --hook-type pre-push`.
