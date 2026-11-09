# Using labbrain

Every command, option, output and exit status. For why each job exists and when to run it, see the
skills; for the rules a wiki follows, see [okf-conventions](../skills/okf-conventions/SKILL.md).

## Running it
```sh
labbrain <command> [options]
python -m labbrain <command> [options]   # the same thing
labbrain --help                          # the commands
labbrain <command> --help                # one command's options
```

If `labbrain` isn't on your PATH, stay in the wiki and run it through a LabBrain checkout:
```sh
cd ~/wiki
pixi run --manifest-path ~/LabBrain/pixi.toml labbrain stale
uv run --project ~/LabBrain labbrain stale
```
Both keep your working directory, so file arguments resolve against the wiki. There is deliberately
no `labbrain` task in `pixi.toml`: pixi runs tasks from the LabBrain folder, so your paths would
resolve there instead.

## Finding the wiki
labbrain works on one wiki per run, which the options call the *vault*. A wiki's root is a folder
whose `index.md` begins with:
```yaml
---
okf_version: "0.2"
---
```
labbrain takes the first of these that applies:
1. **`--vault DIR`,** if you give it.
2. **The wiki you're in:** the outermost folder, from the working directory upwards, whose
   `index.md` declares `okf_version`. *Outermost*, because a wiki can hold several bundles (one per
   git repo), each with a root `index.md` of its own, and links cross between them. To work on one
   inner bundle on its own, pass `--vault`.
3. **`LABBRAIN_VAULT`** from your settings (see [Configuration](configuration.md)).

If none applies, labbrain prints `no vault found: …` and exits with 2. If `--vault` names a folder
that doesn't exist, it prints `no such folder: DIR` and exits with 2.

`--vault` can go before or after the command: `labbrain --vault ~/wiki stale` and
`labbrain stale --vault ~/wiki` are the same.

**Starting a new wiki:** run `labbrain index --vault DIR` on a folder of notes. It writes the root
`index.md`, with `okf_version`, and one in each folder that has notes. From then on, labbrain finds
the wiki without `--vault`.

## File arguments
`stamp`, `links` and `drift-stamp` take file paths.
- **They are relative to where you run the command,** like any shell command, not to the wiki's
  root. From the root you write `Garden/Garden_summary.md`; from inside `Garden/`, `Garden_summary.md`.
  Absolute paths work too.
- **Every path must be inside the wiki.** If one isn't, labbrain prints
  `not inside the vault <wiki>: <path>`, exits with 2 and writes nothing, not even for the paths
  before it that were fine.

## Actors: `--by`
`stamp`, `drift-stamp` and `frontmatter` write who did the work into the files they change:
- **an agent,** as `<tool>/<model>`: `claude-code/claude-opus-5-5`, `open-llm/qwen3-235b`;
- **a person,** as `human:<name>`: `human:ada`.

Never write an email address in an actor. `stamp` and `drift-stamp` have no default, because the
actor must name the model that actually did the work. `frontmatter` falls back to
`LABBRAIN_CONTRIBUTOR` (see [Configuration](configuration.md)).

## Exit status
| status | means |
|---|---|
| 0 | done; or nothing to do, or nothing wrong |
| 1 | `check` found problems, `stale` found stale summaries, or `drift-stamp` was named a file that isn't a summary |
| 2 | the command couldn't run: a missing argument, no wiki found, a path outside the wiki, a missing file, a file `stamp` won't take, or a bad setting. Nothing was written |

So `labbrain check || echo "the wiki needs attention"` works in a script or a scheduled job.

## The commands
| command | writes |
|---|---|
| [`check`](#labbrain-check) | nothing |
| [`stale`](#labbrain-stale) | nothing |
| [`stamp`](#labbrain-stamp) | the summaries' frontmatter |
| [`index`](#labbrain-index) | `index.md` files |
| [`frontmatter`](#labbrain-frontmatter) | new notes' frontmatter |
| [`links`](#labbrain-links) | the notes' link syntax, and the hashes recorded in summaries |
| [`hot`](#labbrain-hot) | nothing |
| [`drift-stamp`](#labbrain-drift-stamp) | the summaries' `drift_verification` |

The examples below are real output from the dummy wiki in `tests/fixtures/vault/`.

### labbrain check
```
labbrain check [--vault DIR]
```
Runs every test below and lists each problem as `<file>: <problem>`. It writes nothing, not even the
`index.md` files it finds out of date. It ends with `OK: vault is OKF 0.2 conformant and current.`
and exits with 0, or with `N problem(s).` and exits with 1.

| problem | means | fix |
|---|---|---|
| `no frontmatter (run: frontmatter)` | a note has no header | `labbrain frontmatter` |
| `frontmatter has no type (run: frontmatter)` | a header without a `type` | `labbrain frontmatter` |
| `index.md may only carry okf_version, and only at a bundle root` | an `index.md` has other frontmatter, or has any below a bundle root | remove it |
| `log.md date headings must be YYYY-MM-DD: …` | a `## ` heading in `log.md` that isn't a date | rewrite it, as `## 2026-01-05` |
| `stale: changed …`, `stale: new …`, `stale: removed …`, `stale: children …` | see [`stale`](#labbrain-stale) | rebuild and stamp the summary (the `index` skill) |
| `drift_verification names a missing file: … (run: links)` | a summary's drift record names a file that was moved or deleted | `labbrain links`, which drops the record |
| `out of date (run: index)` | an `index.md` differs from what `index` would write | `labbrain index` |
| `wikilink [[…]] (run: links)` | a `[[wikilink]]`, in any file | `labbrain links` |
| `broken <link>` | a relative link to a file that doesn't exist, in an agent-written file | fix the link |

Broken links are only reported in agent-written files (summaries, agent guides, session summaries,
paper concepts and `index.md`). A raw note may link to a note that hasn't been written yet.

```
$ labbrain check
log.md: log.md date headings must be YYYY-MM-DD: Jan 5
Garden/Beans.md: no frontmatter (run: frontmatter)
Garden/Garden_summary.md: stale: new Fresh.md
Garden/Garden_summary.md: stale: changed Tomatoes.md
Garden/index.md: out of date (run: index)
Garden/Tomatoes.md: wikilink [[Recipes#Salsa]] (run: links)
Kitchen/Pickling.md: broken Brine.md
…
19 problem(s).
```

### labbrain stale
```
labbrain stale [--vault DIR]
```
For each folder summary, compares the files recorded in its `sources`, and their hashes, with the
files it should cover now. It writes nothing. It prints each stale summary, with one line per reason:

| reason | means |
|---|---|
| `changed <file>` | the file differs from the version the summary was built from |
| `new <file>` | a file the summary should cover, but doesn't record |
| `removed <file>` | a file it records that has gone: deleted, moved, or now covered by a subfolder's own summary |
| `children <list>` | the subfolders that have a summary of their own changed; this lists them now, or says `none` |

It ends with `N stale summary(ies).` and exits with 1 if N isn't 0.

**What a summary covers:** every text file in its folder (`.md`, `.canvas`, `.sh`, `.nix`, `.lock`,
`.txt`, `.py`, `.json`, `.yaml`, `.yml`, `.toml`), and those in subfolders without a summary of their
own. It leaves out other summaries, `index.md`, `log.md`, hidden files and folders, and anything in
another git repo. Images and data files are attachments, not sources.

The hash is taken of the file on disk, so uncommitted edits count.

```
$ labbrain stale
Garden/Garden_summary.md
    new      Fresh.md
    changed  Tomatoes.md
1 stale summary(ies).
```

### labbrain stamp
```
labbrain stamp --by ACTOR SUMMARY... [--vault DIR]
```
Run after rebuilding a summary's text. For each SUMMARY, rewrites the bookkeeping in its frontmatter
from the files on disk:
- `generated: { by: ACTOR, at: <now, in UTC> }`;
- `parent:` the nearest summary above it in the same repo (left out at a repo's root);
- `children:` the summaries of its subfolders (left out if there are none);
- `hash_method: git hash-object`;
- `sources:` every file it covers (see [`stale`](#labbrain-stale)), with its git blob hash.

It keeps `title`, `description`, `verified`, `drift_verification` and any other key, and puts the
keys in a fixed order. If the summary has no `type`, it gets `type: Folder Summary`, and if it has no
`title`, the first `# ` heading becomes one. The body is not touched.

`--by` and at least one SUMMARY are required; without them it prints the usage and exits with 2.

**Every SUMMARY must be a folder summary,** the one `stale` watches in its folder. Given anything
else, such as a raw note, it prints `not a folder summary, so not stamped: <file>`, exits with 2, and
writes nothing, not even the summaries named alongside it. A note would otherwise lose its author to
the actor, and gain the folder's sources.

It prints `stamped <summary>` for each.

```
$ labbrain stamp --by claude-code/claude-opus-5-5 Garden/Garden_summary.md
stamped Garden/Garden_summary.md
```
```yaml
---
type: Folder Summary
title: "Garden — Summary"
description: "Trials of tomatoes and beans in the test garden, with soil notes."
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-09T13:31:54Z }
children:
  - Soil/Soil_summary.md
hash_method: git hash-object
sources:
  - { resource: Beans.md, hash: 5e5d2f0353829c25d5aae347b09dcacef0041330 }
  - { resource: Fresh.md, hash: 0d2507ede621d610e5f7b6114cb5f06e139ccbfc }
  - …
---
```

Stamping marks a summary current, so stamp only once you have read what changed. If only link paths
changed, `labbrain links` moves the hashes forward itself.

### labbrain index
```
labbrain index [--vault DIR]
```
Writes every `index.md` that differs from what it should be, and prints `wrote <file>` for each. A
folder gets an `index.md` when it, or a folder below it, holds a note (any `.md` file other than
`index.md` and `log.md`).

Each `index.md` lists, in this order:
- **`# Summary`:** the folder's summary, or the summary above that covers it (marked
  "Covers this folder."), with its description;
- **`# Notes`:** each note, described by the `description` in its frontmatter, or else by its line in
  the summary's Contents section;
- **`# Subfolders`:** each subfolder that has notes, described by its own summary;
- **`# Other files`:** the files that aren't markdown, such as scripts and data, including those in
  subfolders without notes. Images are left out.

At a bundle root (the wiki's root, or the root of a git repo inside it), the file starts with the
`okf_version` frontmatter.

Two blocks are kept as they are, after the listing: the **map**
(`<!-- map:start -->` … `<!-- map:end -->`) and a folder's **related** block
(`<!-- related:start -->` … `<!-- related:end -->`). Anything else written into an `index.md` by hand
is replaced.

A Contents line has this form, which the `summary-writing` skill describes:
`- [Tomatoes](Tomatoes.md) — tomato trials and their yields (~60 words)`.

```
$ labbrain index
wrote Garden/index.md
```
```markdown
# Summary

* [Garden — Summary](Garden_summary.md) - Trials of tomatoes and beans in the test garden, with soil notes.

# Notes

* [Beans](Beans.md) - where the beans were planted (~10 words)
* [Fresh](Fresh.md)
* [Tomatoes](Tomatoes.md) - tomato trials and their yields (~60 words)

# Subfolders

* [Seeds](Seeds/index.md)
* [Soil](Soil/index.md) - Compost notes for the garden beds.

# Other files

* [data.csv](data.csv)
* [plot.sh](plot.sh) - a script that prints the yields

<!-- related:start -->
* [Tomatoes § Yields](Tomatoes.md#Yields) → [Recipes](../Kitchen/Recipes.md) - the note asks for a link to the salsa recipe
<!-- related:end -->
```

### labbrain frontmatter
```
labbrain frontmatter [--by ACTOR] [--vault DIR]
```
Gives each note without a `type` a minimal header:
```yaml
---
type: Note
generated: { by: human:ada }
---
```
- A note with no frontmatter gets this block.
- A note with frontmatter but no `type` gets `type: Note` added, and `generated` if it has none; the
  rest of its frontmatter is kept.
- A note that already has a `type` is not touched, and neither are `index.md`, `log.md` and
  `*_summary.md`. The body is never changed, and line endings are kept.
- **`annotate: true`** is added as well when the note is signed as you (`--by` is your
  `LABBRAIN_CONTRIBUTOR`, or left out) and your settings say `LABBRAIN_ANNOTATE=true`. It records
  your consent to agents adding metadata to the note's header (see
  [Configuration](configuration.md)). A note whose header already has an `annotate` key keeps its own.

**`--by ACTOR`** is the notes' author. Without it, `frontmatter` uses `LABBRAIN_CONTRIBUTOR`; with
neither, it prints the usage and exits with 2. It prints `added frontmatter: <file>` for each note.

Every note it changes gets the same author, so run it when you know who wrote the new notes. An
agent-written file without a `type` needs its right type by hand: `frontmatter` would call it a note.

```
$ labbrain frontmatter --by human:ada
added frontmatter: Garden/Beans.md
added frontmatter: Garden/Fresh.md
added frontmatter: Kitchen/Shopping.md
```

### labbrain links
```
labbrain links [FILE...] [--vault DIR]
```
Rewrites links as relative markdown links, in each FILE, or in every `.md` file except `index.md`
and `log.md`:

| written as | becomes |
|---|---|
| `[[Beans]]` | `[Beans](Beans.md)` |
| `[[Recipes#Salsa\|salsa]]` | `[salsa](../Kitchen/Recipes.md#Salsa)` |
| `[[Recipes#Salsa]]` | `[Recipes § Salsa](../Kitchen/Recipes.md#Salsa)` |
| `[[#Trials]]` | `[Trials](#Trials)` |
| `[[Spice rack]]` | `[Spice rack](../Kitchen/Spice%20rack.md)` |
| `![[diagram.png\|300]]` | `![diagram.png\|300](diagram.png)` |
| `[Recipes](Recipes.md)`, when `Recipes.md` is in another folder | `[Recipes](../Kitchen/Recipes.md)` |

- **A name resolves the way Obsidian resolves it:** by file name, with the closest match to the
  linking file first. A name with a `/` must match the end of the path.
- **Spaces are written as `%20`.**
- **Links inside code** (`` `…` `` and fenced blocks) are left alone.
- **A link to a file that doesn't exist** is left as it is and reported as
  `  unresolved in <file>: <name>`. Usually it is a note that hasn't been written yet.

Then it **carries the summaries' hashes forward.** A summary whose recorded hash matched a file
before the rewrite gets the file's new hash, so a link-only edit doesn't make it look stale. The same
goes for the hashes in `drift_verification`, and a drift record of a file that no longer exists is
dropped. Real changes made before the run still show as stale.

It prints `rewrote links: <file>` and `carried hashes forward: <summary>`, and exits with 0.

```
$ labbrain links
rewrote links: Garden/Beans.md
rewrote links: Garden/Fresh.md
rewrote links: Garden/Garden_summary.md
rewrote links: Garden/Tomatoes.md
  unresolved in Garden/Tomatoes.md: Missing note
  unresolved in Kitchen/Pickling.md: Brine.md
rewrote links: Kitchen/Recipes.md
```

### labbrain hot
```
labbrain hot [--days D] [--min N] [--recheck R] [--vault DIR]
```
Lists the files that change most and, for each one, the agent-written files to check against it
for drift. It writes nothing, and exits with 0.

- **`--days D`** (default 30) and **`--min N`** (default 3): a file is *hot* when it has N or more
  changes in the last D days. A change is a commit that touched the file, plus one if it has
  uncommitted edits. Only files that some summary is built from are considered.
- **`--recheck R`** (default 3): a summary that was checked against the file is *due* again once the
  file's changes, plus the edits to the summary's description or body, add up to R since the check.

```
$ labbrain hot
1 hot file(s): 3 or more changes in the last 30 days (commits, plus 1 for uncommitted edits).
1 due for a drift check: a summary never checked against it, or 3 or more changes to the file and edits to the summary since its check.

  4  Garden/Tomatoes.md   (3 commit(s) + uncommitted)   DUE
       summary   Garden/Garden_summary.md (stale: changed; never checked: DUE)
       cited by  Garden/index.md (1 link; no tag: checked when the file is due)
       cited by  Kitchen/Session_2026-01-05.md (1 link; session summary: never checked)
       cited by  index.md (1 link; no tag: checked when the file is due)
```

For each hot file:
- **the first line** has its number of changes, its path, the commits and whether it has uncommitted
  edits, and `DUE` or `skip: checked`;
- **`summary`** is the summary that hashes the file: whether it is `current`, `stale: changed` or
  `stale: new`, and its drift state:
  - `never checked: DUE`;
  - `checked <date>, K changes since`, with `+ M summary edits` if there were any, and `: DUE` once
    they reach R;
- **`cited by`** is each other agent-written file that links to it, with the number of links:
  - another folder summary has a drift state, as above;
  - `session summary: never checked`: a session summary is a dated record, so it is never rebuilt;
  - `no tag: checked when the file is due`: a file without drift records of its own (an `index.md`
    map or related block, an agent guide, a paper concept), checked whenever the hot file is due.

A hot file is `DUE` when any folder summary listed for it is due.

### labbrain drift-stamp
```
labbrain drift-stamp --by ACTOR FILE [SUMMARY...] [--recheck R] [--vault DIR]
```
Records that FILE was checked for drift. Run it after the drift job has compared and fixed the
summaries. In each summary, it writes one entry in `drift_verification`, replacing any earlier entry
for FILE:
```yaml
drift_verification:
  - { resource: Tomatoes.md, hash: <FILE's blob hash now>, commit: <FILE's last commit>, summary_hash: <hash of the summary's description and body>, at: <now>, by: <ACTOR> }
```
- **With no SUMMARY,** it writes every summary that `hot` shows as due for FILE. `--recheck R`
  (default 3) decides which are due, as in `hot`.
- **With SUMMARY…,** it writes those, due or not. Use this to record a check you held back while a
  question about it was open.
- **`summary_hash`** covers the summary as it is after your fixes, so the fixes don't count as edits
  at the next scan.
- `--by` and FILE are required, and FILE must exist; otherwise it exits with 2.

It prints `drift-stamped <summary>` for each, or `nothing due for FILE`. A named file that isn't a
folder summary can't hold the entry: it prints `  not a summary, no tag: <file>`, writes the
others, and exits with 1.

```
$ labbrain drift-stamp --by claude-code/claude-opus-5-5 Garden/Tomatoes.md
drift-stamped Garden/Garden_summary.md
$ labbrain drift-stamp --by claude-code/claude-opus-5-5 Garden/Tomatoes.md
nothing due for Garden/Tomatoes.md
```

## Common sequences
**After notes changed** (the code steps of the `index` skill):
```sh
labbrain stale
labbrain frontmatter --by human:<author>
labbrain links
# rebuild each stale summary (the summary-writing skill), then:
labbrain stamp --by <tool>/<model> Garden/Garden_summary.md
labbrain index
labbrain check
```

**A drift scan** (the code steps of the `drift` skill):
```sh
labbrain stale        # must list nothing; if it does, run the index skill first
labbrain hot
# compare and fix the due summaries (the drift skill), then, for each hot file checked:
labbrain drift-stamp --by <tool>/<model> Garden/Tomatoes.md
labbrain check
```

**In a script, a git hook or a scheduled job:** `labbrain check` exits with 1 when anything is off.
