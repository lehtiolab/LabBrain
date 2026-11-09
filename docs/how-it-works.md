# How LabBrain works

## The wiki
A lab wiki, here, is a folder of markdown notes kept in git and written in the
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2). Each file starts with a short YAML header, its *frontmatter*, whose `type` says what
the file is.

There are two kinds of file:
- **Raw notes,** written by people. Their text stays as their author wrote it. LabBrain makes two
  mechanical edits: it adds a minimal header, and it rewrites `[[wikilinks]]` as ordinary relative
  links. Agents may add metadata to a note's header, such as a description, only if its author
  allows it, and what they add is recorded in the header.
- **Agent-written files,** which make the notes findable:
  - a **folder summary** (`<Folder>_summary.md`) for each folder with real content. It says what
    the notes say, and links every claim to the note and heading it comes from;
  - an **`index.md`** in each folder, listing its summary, notes and subfolders, one line each;
  - the **map,** in the root `index.md`: where each topic, project and person lives;
  - a **`log.md`** in each repo: what changed, by date.

A wiki can span several git repos. Each repo is a *bundle*, with its own root `index.md`, and links
can cross between them.

The dummy wiki the tests use, in `tests/fixtures/vault/`, is a garden and a kitchen:
```
vault/
├── index.md                the root listing and the map; it declares okf_version
├── log.md
├── Garden/
│   ├── index.md            a generated listing
│   ├── Garden_summary.md   agent-written
│   ├── Tomatoes.md         raw notes
│   ├── Beans.md
│   └── Soil/
│       ├── Soil_summary.md
│       └── Compost.md
├── Kitchen/
│   └── …
└── Shelf/                  a git repo of its own: a second bundle
```

## What goes wrong without upkeep
Nothing in a folder of notes knows when a note changes. So:
- summaries go on describing the notes as they used to be;
- the listings miss new notes, and the map stops leading to them;
- an agent searching the wiki answers confidently from an out-of-date picture.

Upkeep by hand doesn't happen. Upkeep by a model alone is expensive, because it rereads everything,
and hard to trust, because it writes values it should have computed.

## Code works things out, and a model reads
LabBrain splits every job in two:

| | code | a model |
|---|---|---|
| does | whatever follows from file names, paths, dates, git hashes or fixed text | whatever needs a note read and understood |
| for example | which summaries are stale; a summary's list of sources and their hashes; the `index.md` listings; which files change most | a summary's title, description and body; the map; whether a summary still says what its notes say |
| costs | nothing, and gives the same answer every time | tokens, and its output needs checking |

Code also decides what runs and which files may change: **the LLM is not the scheduler.** A model is
called only where a note has to be read, and a job with nothing to do stops before it calls one.

## Knowing a summary is stale without rereading it
When a summary is built, `labbrain stamp` records every file it was built from, with that file's
**git blob hash** (`git hash-object`):
```yaml
sources:
  - { resource: Tomatoes.md, hash: f4acfec931e9e58a92166ca6816c36412232cfa1 }
```
Later, `labbrain stale` hashes the files again. A different hash means the note changed after the
summary was written. Because the hash is git's own id for that content, `git cat-file -p <hash>`
prints the exact version the summary was built from, so the change can be shown as a diff.

Hashes don't catch everything. A summary can be current by hash and still say something its notes
no longer say: it has *drifted*. The drift job checks for that, starting with the notes that change
most (`labbrain hot`).

## The parts of LabBrain
| part | what it is | where |
|---|---|---|
| functions | Python that does the mechanical work | `src/labbrain/okf/` |
| the command | `labbrain <command>`: the functions, run from a shell | `src/labbrain/cli.py` |
| skills | instructions an LLM reads to do a job | `skills/` |
| patterns | what agents learn from their runs (draft) | `patterns/` |
| settings | your name as a contributor, and your default wiki | `env/` |

[Functions and skills](functions-and-skills.md) explains the difference between the first and the third.

## A job, start to finish
Someone edits `Garden/Tomatoes.md` and adds `Garden/Fresh.md`. The *index* job brings the wiki up
to date:

| step | done by | what happens |
|---|---|---|
| `labbrain stale` | code | `Garden/Garden_summary.md`: `new Fresh.md`, `changed Tomatoes.md` |
| `labbrain frontmatter --by human:ada` | code | `Fresh.md` gets `type: Note` and its author |
| `labbrain links` | code | wikilinks become relative links |
| rebuild `Garden_summary.md` | **model**, following the `summary-writing` skill | reads what changed in the two notes, and updates the claims |
| `labbrain stamp --by <model> Garden/Garden_summary.md` | code | records the new hashes |
| the map and the log | **model** | adds `Fresh.md` to the map, and a log entry |
| `labbrain index` | code | regenerates the listings |
| `labbrain check` | code | must end with `OK` |
| `labbrain commit --by <model> -m "index: …"` | code | commits the job's work in each repo; a person pushes it |

Only two of the nine steps call a model.

## Two ways to run a job
- **By hand.** You bring your own LLM (Claude Code, Codex, a local model, anything that reads
  files and runs commands), load the skill for the job, such as `skills/index/SKILL.md`, and ask.
  The skill tells the model why the job exists, which commands to run, what to write itself, and
  when to stop and ask you.
- **At night, unattended** *(planned)*. A scheduled job runs the code steps itself and calls a
  model only for the steps that need one, with the same skill as the model's instructions. A quiet
  night costs nothing.

## Skills and patterns evolve in each wiki
The skills in this repo are seeds. Each wiki keeps its own copies in its own `skills/`, and they
change there as the lab learns what works. Each run will leave a trace in the wiki's
`patterns/traces/`, and the patterns drawn from many runs go in its `patterns/`
(see [patterns/README.md](../patterns/README.md)).

A skill or pattern that works beyond one lab comes back here by pull request, with the lab's data
taken out. Raw traces never leave the wiki.

## What exists today
- **Works:** the nine commands, the five wiki skills, and the settings in `env/`.
- **Draft:** the trace and pattern formats.
- **Planned:** the code that calls a model (`llm()`), the nightly run, search code, an MCP server,
  and task boards as a separate feature.
