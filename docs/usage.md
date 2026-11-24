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
`stamp`, `links`, `drift-stamp` and `canvas` take file paths, and `hierarchy` takes folders.
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
| 2 | the command couldn't run: a missing argument, no wiki found, a path outside the wiki, a missing file, a file `stamp` won't take, a file `canvas` can't draw, a `hierarchy` folder that isn't one, a bad setting, or a bad wiki config. Nothing was written |

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
| [`canvas`](#labbrain-canvas) | pictures in `_maps/`, which git ignores |
| [`hierarchy`](#labbrain-hierarchy) | `_maps/hierarchy.yaml` and its picture |
| [`graph`](#labbrain-graph) | `_maps/graph.json`, the wiki's graph |

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
own. It leaves out other summaries, `index.md`, `log.md`, hidden files and folders, anything in
another git repo, `_maps/` at the root of the wiki or of any git repo in it, where labbrain draws
its pictures, and the wiki's own config, `labbrain.yaml` and `topics.yaml` at its root. Images and data files are attachments, not sources.

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
dropped, along with the `drift_verification` key itself once its last record goes. Real changes
made before the run still show as stale.

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

### labbrain canvas
```
labbrain canvas FILE... [--view canvas|html] [--vault DIR]
```
Draws each `.json`, `.yaml` or `.yml` FILE as a tree of boxes, so you can see how the data nests.
- **The view** is `--view`, else `LABBRAIN_VIEW` (see [Configuration](configuration.md)), else
  `canvas`:
  - `canvas`: an Obsidian canvas ([JSON Canvas](https://jsoncanvas.org)), which Obsidian opens;
  - `html`: one web page, with nothing loaded from the internet.
- **The picture goes in `_maps/` at the wiki root,** at the file's own path with the view's
  extension: `Garden/plan.yaml` becomes `_maps/Garden/plan.canvas`. With `--vault` naming an inner
  bundle, the root is that bundle's. A file already in `_maps/` gets
  its picture beside it. Drawing a file again replaces its picture.
- **`_maps/` is never part of the wiki.** labbrain writes `_maps/.gitignore`, so git ignores the
  folder, and no other command looks inside it: no summary covers it, and no listing shows it. That
  holds for a `_maps/` at the root of any git repo in the wiki too, such as one drawn with `--vault`.

**What goes in a box:**
- A mapping or a list is a box, titled by its key. A list item has no title.
- A value that is neither, such as a number or a short text, is a line in its parent's box:
  `budget: 120`, or `- basil` for a list item. Each nested mapping or list is a box of its own, with
  an arrow from its parent.
- **Some keys shape the picture** instead of showing as `key: value`:

  | key | does |
  |---|---|
  | `title` | titles the box |
  | `description` | a line in the box, without its key |
  | `path` | when it names a file in the wiki, the title links to that file |
  | `children` | a list whose items are boxes under this one, without a `children` box between |
  | `links` | wiki files this box links to: one line at the end of the box, `→ Garden — Summary · Beans`, each name a link to its file. A name is the file's `title`, else its file name. There are no arrows for links: on a real wiki they tangled |

A `path` or a link that isn't a file in the wiki is shown as text. In a canvas, click a title or a
link's name to open its file. In a page, they are links to the files.

YAML is read with PyYAML's `safe_load`, so a file can't make labbrain run anything. A file that
isn't JSON or YAML, doesn't exist, or doesn't parse is refused with `can't draw <file>: <why>`. Every
FILE is read before any picture is written, so one bad file means nothing is written, and the exit
status is 2.

```
$ labbrain canvas Garden/plan.yaml
drew _maps/Garden/plan.canvas
$ labbrain canvas --view html Garden/plan.yaml Garden/Tomatoes.md
can't draw Garden/Tomatoes.md: not a .json, .yaml or .yml file
```

### labbrain hierarchy
```
labbrain hierarchy [FOLDER...] [--view canvas|html] [--vault DIR]
```
Writes the folder summaries in each FOLDER as one tree, then draws it beside, as
[`canvas`](#labbrain-canvas) does. With no FOLDER, it draws the whole wiki.

| FOLDER | writes |
|---|---|
| none | `_maps/hierarchy.yaml`, and `_maps/hierarchy.canvas` or `.html` |
| `Garden` | `_maps/Garden/hierarchy.yaml`, and `_maps/Garden/hierarchy.canvas` or `.html` |

Each is rewritten on every run. A FOLDER is relative to where you run the command, like a file
argument: from inside `Garden/`, `labbrain hierarchy .` draws `Garden`. A FOLDER that doesn't exist
is refused with `not a folder: <folder>`, and nothing is written. It reads only the summaries'
frontmatter and links: no model, and no note is read.
- **Each summary sits under the summary of the folder above it,** as `stamp` would record its
  `parent`.
- **The top of the tree** is FOLDER's own summary, when every other summary in FOLDER sits under
  it. Otherwise it is the folder itself, titled with its name, with its `index.md` as its `path`.
  For the whole wiki that is usually the wiki, because the top summary of each git repo in it has
  no parent.
- **Each summary has** its `title`, its `path`, its `description` if it has one, its `links` and
  its `children`.
- **`links` are what its text links to outside its own part of the tree:**
  - a link to a note becomes a link to the summary that covers the note, inside FOLDER or not,
    so a part of the wiki shows how it connects to the rest;
  - a link to a file no summary covers stays a link to the file;
  - links to its own notes, its parent and its children are left out, since the tree shows them;
  - broken links, links inside code and web links are left out.

```
$ labbrain hierarchy
wrote _maps/hierarchy.yaml
drew _maps/hierarchy.canvas
$ cat _maps/hierarchy.yaml
# Written by `labbrain hierarchy` from the folder summaries, and rewritten on every run.
title: vault
path: index.md
children:
- title: Garden — Summary
  path: Garden/Garden_summary.md
  description: Trials of tomatoes and beans in the test garden, with soil notes.
  links:
  - Kitchen/Recipes.md
  children:
  - title: Soil — Summary
    path: Garden/Soil/Soil_summary.md
    description: Compost notes for the garden beds.
- title: Shelf — Summary
  path: Shelf/Shelf_summary.md
  description: Jars kept on the shelf.
```
The picture is only as current as the summaries: run `labbrain stale` first.

### labbrain graph
```
labbrain graph [--vault DIR]
```
Brings the wiki's graph up to date in `_maps/graph.json`. The graph is a cache: code builds it from
the wiki, nobody edits it, and git ignores it, like everything in `_maps/`. Throw it away and the
next run builds the same one.

- **Each markdown file is a node,** except `index.md` and `log.md`, which link to everything around
  them. A node has the file's path as its `id`, and its `type`, `title`, `description`, `tags` and
  `topics` from its header, where it has them. A `title` comes from the header, else the first
  `# heading`, else the file name. `hash` is the file's git blob hash.
- **Edges have a `kind`:**

  | kind | from | to |
  |---|---|---|
  | `link` | a file | a file its text links to, by `[[wikilink]]` or relative link, resolved the way Obsidian resolves it |
  | `covers` | a summary | a note it is built from (one of its `sources`) |
  | `child` | a summary | the summary of a subfolder under it |

  Links inside code, to files that don't exist, to files that aren't markdown, and to the file
  itself make no edge.
- **The same wiki always gives the same file:** nodes and edges are sorted, and nothing in it
  depends on the time or on who ran it. Anyone who builds it from the same commits gets the same
  bytes.
- **Only changed files are read.** `_maps/graph-cache.json` keeps what was read from each file,
  under the file's git blob hash, and a file whose hash hasn't changed isn't read again. Links are
  resolved again on every run, since a new file can change where `[[Beans]]` leads.

```json
{
 "title": "vault",
 "nodes": [
  {"id": "Garden/Garden_summary.md", "type": "Folder Summary", "title": "Garden — Summary",
   "description": "Trials of tomatoes and beans in the test garden, with soil notes.", "hash": "…"},
  {"id": "Garden/Tomatoes.md", "type": "Note", "title": "Tomatoes", "hash": "…"}
 ],
 "edges": [
  {"from": "Garden/Garden_summary.md", "to": "Garden/Soil/Soil_summary.md", "kind": "child"},
  {"from": "Garden/Garden_summary.md", "to": "Garden/Tomatoes.md", "kind": "covers"},
  {"from": "Garden/Tomatoes.md", "to": "Kitchen/Recipes.md", "kind": "link"}
 ]
}
```

```
$ labbrain graph
wrote _maps/graph.json: 13 files; 16 link, 5 covers and 1 child edges; 13 file(s) read, the rest unchanged
$ labbrain graph
wrote _maps/graph.json: 13 files; 16 link, 5 covers and 1 child edges; 0 file(s) read, the rest unchanged
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
