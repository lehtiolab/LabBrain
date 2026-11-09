---
name: okf-conventions
description: The rules an OKF lab wiki follows and that labbrain checks. Covers concept types, note and folder-summary frontmatter, provenance with git blob hashes, generated index.md listings, log.md, drift verification and relative links. Load it alongside the index, drift or summary-writing skills, or when a file's frontmatter or a labbrain message needs explaining.
---

# OKF conventions in a lab wiki

The wiki is an [Open Knowledge Format v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundle: a directory of markdown files, each with YAML frontmatter that carries a `type`. labbrain
adds git blob hashes to OKF's provenance, so code can check whether a summary is stale without
rereading the notes.

## Two kinds of file
- **Raw notes are written by people, and their text stays as written.** Never rewrite, tidy,
  shorten or add to a note's text, not even a list of links, unless its author asks. Code makes two
  kinds of edit, both mechanical: `labbrain frontmatter` adds a minimal header, and `labbrain links`
  rewrites link syntax. Metadata in a note's header is allowed only with its author's consent
  (below).
- **Everything else is agent-written:** folder summaries, the `index.md` listings with their map and
  related blocks, `log.md`, session summaries and paper-bundle concepts. Agent content goes there,
  never into a note. When a note asks agents for something ("link this to …"), do it in the related
  block of the note's folder's `index.md`.

## Concept types
Every `.md` file except `index.md` and `log.md` needs a `type`.

| type | what it is |
|---|---|
| `Note` | A raw note. Its frontmatter is `type: Note` and `generated: { by: human:<author> }`, plus `annotate: true` and agent metadata if its author allows it (below). |
| `Folder Summary` | The agent-written summary of a folder (below). |
| `Session Summary` | An agent's dated record of a working session. It is never rebuilt, and `stale` ignores it. |
| `Agent Guide` | An instruction file for agents. |
| `Paper`, `Method`, `Algorithm`, `Finding`, `Dataset`, `Software`, `Reference` | Concepts an agent drafts from one published paper, in a folder of their own. They keep `status: draft` until a person checks them against the paper and adds `verified`. |

**Actors** (`generated.by`, `verified.by`):
- `<tool>/<model>` for an agent, e.g. `claude-code/claude-opus-5-5` or `open-llm/qwen3-235b`;
- `human:<name>` for a person.

Never put an email address in an actor, or anywhere else in the wiki.

## Metadata on raw notes
A note's header can carry metadata for agents, such as a `description`, but only if its author agrees.
- **`annotate: true`** in the header is the author's consent. Without it, the answer is no.
  `labbrain frontmatter` writes it into new notes whose author set `LABBRAIN_ANNOTATE=true`; an
  author can also add or remove it by hand. Never add it for someone else.
- **`generated` stays the author's.** It names who wrote the note, and an agent never replaces it.
- **`annotated` records what agents added,** one entry per agent, which updates its own entry or adds one:
  ```yaml
  annotated:
    - { by: <actor>, at: <YYYY-MM-DDTHH:MM:SSZ>, keys: [description] }
  ```
- **No labbrain command writes agent metadata yet,** so don't add any by hand. Like the rest of the
  bookkeeping, it will be written by code, with the model supplying only the value.

## Folder summaries
There is one summary per folder with real content. It is named `<Folder>_summary.md` and lives in
that folder. It covers the folder's notes and every subfolder that has no summary of its own.

```yaml
---
type: Folder Summary
title: "<Folder> — Summary"
description: "<one sentence; index.md shows it next to the folder>"
generated: { by: <actor>, at: <YYYY-MM-DDTHH:MM:SSZ> }
drift_verification:              # written by labbrain drift-stamp; absent until then
  - { resource: <file>, hash: <blob>, commit: <short hash>, summary_hash: <hash>, at: <time>, by: <actor> }
parent: ../<Parent>_summary.md   # absent at a repo root
children:                        # summaries of subfolders; absent if none
  - <Sub>/<Sub>_summary.md
hash_method: git hash-object
sources:                         # every file it was built from, with its git blob hash
  - { resource: <path relative to the folder>, hash: <blob> }
---
```

- **You write `title`, `description` and the body. Code writes the rest.** Run
  `labbrain stamp --by <actor> <summary>`: it lists the sources, hashes them, and sets `generated`,
  `parent` and `children`. Never fill these in by hand.
- **`sources`** are every text file in the folder, plus the files in subfolders that have no summary
  of their own. They never include the summary itself, `index.md` or `log.md`.
- **Why a hash:** it is the git blob id. `git cat-file -p <hash>`, run in the owning repo, prints the
  exact version the summary was built from; diff that against the note to see what changed.
  `labbrain stale` compares the recorded hashes with the files on disk.
- **Summaries of code projects** also carry `code_repo`, `code_repo_url` and `repo_commit`. For
  these, the repo is the source of truth for the current state.
- **Human review** is OKF's `verified: { by: human:<name>, at: <time> }`. A `verified.at` older than
  `generated.at` means the review predates the current text.

## index.md and log.md (reserved names)
- **`index.md`** exists in every folder that has notes. It lists the folder's summary, notes,
  subfolders and other files, each with a one-line description.
  - `labbrain index` generates the listing: never edit it by hand.
  - Two blocks are maintained by agents, and `labbrain index` keeps them as they are:
    - the **map**, in the root `index.md` only, between `<!-- map:start -->` and `<!-- map:end -->`;
    - a folder's **related** block, between `<!-- related:start -->` and `<!-- related:end -->`: the
      links its notes ask for, one per line, as
      `* [Note § Heading](Note.md#Heading) → [Target](path) - what the note says`.
- **Frontmatter in `index.md`:** only a bundle root's `index.md` has any, and it holds only
  `okf_version: "0.2"`.
- **`log.md`** at each bundle root records changes, newest first, under `## YYYY-MM-DD` headings.

## Drift verification
A summary can be current by hash and still say something its notes no longer say. The `drift`
skill checks summaries against the files that change most.
- **Each check is recorded** in the summary's `drift_verification`, one entry per file checked.
- **A summary is due again** when the changes to the file, plus the edits to the summary's
  description or body, add up to 3 since the check.
- **Only summaries carry the entry.** It is not OKF's `verified`.
- **Only `labbrain drift-stamp` writes it,** never a person or an agent by hand.

## Links
- **Use relative markdown links everywhere:** `[Note](../Folder/Note.md#Heading)`, with spaces
  written as `%20`. Embed images as `![name.png](name.png)`.
- **Obsidian can write them:** in Settings → Files & links, turn off "Use [[Wikilinks]]" and set
  "New link format" to "Relative path to file".
- **`labbrain check` flags wikilinks; `labbrain links` converts them.** It also keeps the summaries'
  recorded hashes current, so an edit that only changes links doesn't look like a change.

## Several repos
A wiki can span several git repos. Each one is a bundle, with its own `index.md` and `log.md`.
Links can cross between them, and each change is committed in the repo that owns the file.
Agents commit, with `labbrain commit`; they never push. A person pushes.

## Commands
| command | what it does | writes |
|---|---|---|
| `labbrain check` | everything below; exits with 1 if anything is off | nothing |
| `labbrain stale` | summaries whose sources changed, were added or were removed | nothing |
| `labbrain stamp --by ACTOR SUMMARY...` | records provenance after a rebuild | the summaries' frontmatter |
| `labbrain index` | regenerates every `index.md` listing | `index.md` files |
| `labbrain frontmatter --by ACTOR` | adds a minimal header to notes without a type | new notes' frontmatter |
| `labbrain links [FILE...]` | turns wikilinks into relative links and carries hashes forward | notes' link syntax, summaries' hashes |
| `labbrain hot [--days D] [--min N] [--recheck R]` | lists often-changed files, the files that cite them, and which are due a drift check | nothing |
| `labbrain drift-stamp --by ACTOR FILE [SUMMARY...]` | records a drift check | summaries' `drift_verification` |
| `labbrain commit --by ACTOR -m MESSAGE` | commits a job's changes in each repo, once `check` passes; never pushes | a commit per repo |

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
