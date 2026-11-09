---
name: index
description: Bring an OKF lab wiki's headers, folder summaries, index.md listings and map up to date after notes were added, edited, moved or deleted. Use when asked to index, sweep or update the wiki, or after a batch of note changes. labbrain does the mechanical steps, and the model rebuilds stale summaries and the map. The same steps also run unattended as a nightly job.
---

# index: bring the wiki up to date

## Why
People add and edit notes, and nothing else in the wiki knows. Without this job, folder summaries
go on describing notes as they used to be, the `index.md` listings miss new notes, and the map stops
leading to them. Search then answers confidently from an out-of-date picture.

## When
Run it after notes change, and nightly as a scheduled job. If `labbrain stale` lists nothing and
`labbrain check` ends with `OK`, there is nothing to do, so stop.

## Code versus model
If a value can be worked out from file names, paths, dates, hashes or fixed text, code fills it in.
If it needs a note to be read, the model writes it.

| step | done by |
|---|---|
| headers on new notes | code: `labbrain frontmatter` |
| wikilinks to relative links | code: `labbrain links` |
| which summaries are stale, and why | code: `labbrain stale` |
| a summary's title, description and body | **the model** (the `summary-writing` skill) |
| a summary's sources, hashes, parent, children and time | code: `labbrain stamp` |
| parent summaries, related links, the map, the log entry | **the model** |
| the `index.md` listings | code: `labbrain index` |
| conformance | code: `labbrain check` |

The nightly job runs the code steps itself, and calls a model only for the summaries whose notes
changed, so a quiet night costs nothing. When you run this skill by hand, you do both parts.

## Steps
1. **Find what changed.** In each git repo of the wiki, run `git -C <repo> status --porcelain -uall`.
   Then run `labbrain stale`. It lists every summary those changes touch, with the reason: a
   `changed`, `new` or `removed` source, or `children`.
2. **Headers.** `labbrain frontmatter --by human:<author>` gives every new note `type: Note` and its
   author. If you don't know who wrote the new notes, stop and ask. An agent-written file without a
   `type` gets the right one by hand (see `okf-conventions`).
3. **Links.** `labbrain links` converts wikilinks and repairs links that were shortened to a bare
   file name. It also moves the summaries' recorded hashes forward, so link-only edits don't look
   stale. The links it reports as unresolved point at notes that aren't written yet, so leave them.
4. **Rebuild each stale summary,** following the `summary-writing` skill. Then run
   `labbrain stamp --by <your actor> <summary>` for each one.
5. **Carry changes up** to the parent summaries (see `summary-writing`).
6. **Links that notes ask for.** When a new or changed note asks agents for a link ("link this to
   …"), add it to the related block of its folder's `index.md`, creating the block if there isn't
   one. Never add it to the note. If the target is unclear, stop and ask.
7. **Listings.** `labbrain index` regenerates every `index.md` listing and keeps the map and the
   related blocks as they are.
8. **The map** in the root `index.md`. Add every new note and folder to its section, with a few
   words on what it is, and fix the entries for files that were moved, renamed or deleted. Every
   folder should be reachable from the root `index.md`.
9. **Log.** Add one entry under today's date (`## YYYY-MM-DD`) to the `log.md` of each repo whose
   files changed. Say which notes got headers, which summaries were rebuilt, re-stamped or created,
   and what changed in the map.
10. **Check.** `labbrain check` must end with `OK`. If it doesn't, fix what it points to (usually a
    missing `stamp` or `index`) before you report.
11. **Commit.** `labbrain commit --by <your actor> -m "index: <what changed>"`. It commits in each
    repo with changes. Never push: a person does that.

## Rules
- **Never change a raw note,** apart from the mechanical edits in steps 2 and 3.
- **Never write provenance by hand:** `sources`, hashes, `generated` and `drift_verification` are
  written only by `labbrain`.
- **Agent content goes where the layout puts it:** summaries, `index.md` blocks, `log.md`. Don't
  create new places for it.

## Stop and ask
Stop, and don't start the next step, when:
- the request is ambiguous;
- a note asks for something this skill doesn't allow;
- two notes disagree, and a summary would have to pick a side;
- you don't know who wrote a note.

Say what you found, the options and the one you recommend, then wait for an answer. Don't note the
question and carry on: a question buried at the end of a long run never gets seen.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
