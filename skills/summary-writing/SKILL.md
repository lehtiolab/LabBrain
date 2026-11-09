---
name: summary-writing
description: How to write or rebuild a folder summary in an OKF lab wiki, so that every claim traces back to a note and says what that note says. The index skill uses it to rebuild stale summaries and the drift skill to fix drifted ones. Load it whenever a Folder Summary is written or edited.
---

# Writing a folder summary

A folder summary lets people and agents find their way into a folder without reading every note.
It is only useful if it is faithful: it says what the notes say, every claim can be traced, and
nothing else is added.

## What goes in
- **Only what the notes say.** No inferred or suggested connections, and no general knowledge. Don't
  turn the author's reasoning into something it isn't. If you think a link should exist, suggest it
  to the author; it doesn't go in the summary.
- **Every claim links to its source,** down to the heading: `[Note § Heading](Note.md#Heading)`.
- **The body has these sections, in this order:** Intent & purpose · Current state · Key points ·
  Open questions · Connections · Contents.
- **Contents has one line per note,** in this exact form, because `labbrain index` reads it to
  describe the notes in `index.md`:
  `- [Note](Note.md) — what it is (~N words)`.
  Child summaries share one line:
  `- Child summaries: [Sub](Sub/Sub_summary.md) — what it covers`.
- **The `title` is `"<Folder> — Summary"`.** The `description` is one sentence, which `index.md`
  shows next to the folder.
- **Leave the rest of the frontmatter to `labbrain stamp`** (see `okf-conventions`).

## The author's voice
Raw notes often pair a structured claim with the author's informal reaction to it.
- **Lead with the structured argument,** not the informal tone. Where the reaction adds a distinct
  position, keep it as a brief, neutral qualifier.
- **Never drop a qualifier so that the summary says the opposite** of what the author believes.
  Never harden a hedged position, and never soften a firm one.
- **Never invent the author's voice.** When writing in the first person for an author, include only
  what they said, or what follows directly from it. Leave out invented detail, even if it would make
  the text sound more natural, or offer it as a clearly labelled suggestion.

## Rebuilding after a change
`labbrain stale` gives a reason for each stale summary:
- **changed source:** see what changed with
  `git -C <repo> cat-file -p <recorded hash> | diff - <file>`. If the old blob was never committed,
  reread the whole note. Update the claims the change affects, and check every claim that cites a
  changed section. If only link paths changed, re-stamp without rebuilding.
- **new source:** read it, then add its Contents line and its claims in the right sections.
- **removed source:** drop the claims that only it supported, and give its last hash in the log.
- **children:** a subfolder gained or lost its own summary. Update the Contents line for child summaries.

A new folder gets its own summary when more than one of its notes has real content. An empty folder,
or one with a single note, stays covered by its parent's summary.

When you have finished writing, run `labbrain stamp --by <your actor> <summary>`. It records the
sources and their hashes, which you never write by hand.

## Carrying changes up
When a rebuild changes a summary's description, or what it says about the folder's state, update
the lines about that folder in its parent summary, and so on up to the repo root. If a parent's own
sources didn't change, edit it in place without re-stamping it.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
