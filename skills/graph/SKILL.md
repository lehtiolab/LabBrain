---
name: graph
description: Curate the wiki's graph, the graph agent's job. Give folder summaries, other agent-written files and the notes whose authors allow it topics from the wiki's vocabulary (topics.yaml), so that code-only search finds files by subject without a model reading the wiki. Use when asked to curate the graph, tag files or add topics, and as a nightly job after the index skill. labbrain curate lists the work; the model reads only those files and sets topics with labbrain topics, from the vocabulary first and at most three new per file; labbrain vocabulary adds the new ones to topics.yaml for a person to review; code proposes links between files that share topics, and people accept or turn them down. Experimental.
---

# graph: curate the wiki's topics

## Why
`labbrain search` and the graph page find files by their headers first: title, description, path,
tags and topics. That costs nothing, but only if the headers say what the files are about. A
summary's `topics`, taken from the wiki's vocabulary, do that for its whole folder: a search for
"tumour" finds the summaries about cancer without a model reading a single note.

The vocabulary is in `topics.yaml` at the wiki root, and it grows with the wiki. Free tags drift as
soon as several people write them, so this job chooses from the vocabulary first, and adds a new
topic only when nothing in it fits: at most three per file. `labbrain vocabulary` writes the new
ones into `topics.yaml`, where a person reviews them: keeps, merges or vetoes each.

## When
- **Nightly, after the `index` skill,** and whenever someone asks to curate the graph, tag files or
  add topics.
- **Only when the summaries are current:** topics describe what a summary says. If `labbrain stale`
  lists anything, run the `index` skill first.
- **Only when there is work:** `labbrain curate` exits with 0 and says
  `nothing for the graph agent to do` when there is none. Then stop: a quiet night costs nothing.

## Code versus model
| step | done by |
|---|---|
| which summaries are stale | code: `labbrain stale` |
| which files need topics, which carry vetoed topics, which no link reaches, which links are proposed | code: `labbrain curate` |
| reading a listed file and choosing its topics from the vocabulary | **the model** |
| checking the topics against the vocabulary, and writing them | code: `labbrain topics` |
| a raw note: whether its author allows it, and the `annotated` record | code: `labbrain topics` |
| a new topic, when nothing in the vocabulary fits | **the model**; a person reviews it in `topics.yaml` |
| adding new topics to `topics.yaml`, and listing what waits for review | code: `labbrain vocabulary` |
| links between files that share topics | code proposes them; a person adds the link, or turns it down with `labbrain reject` |
| bringing the graph up to date | code: `labbrain graph` |

## Steps
1. **Check the summaries are current** with `labbrain stale`. If it lists anything, run the `index`
   skill first.
2. **List the work** with `labbrain curate`. If it says `nothing for the graph agent to do`, stop.
   It lists ingested files only: a file without a header, or not yet in its folder's `index.md`,
   is left out, and is the `index` skill's work, not yours.
3. **Read the vocabulary:** `topics.yaml`, and the new topics curate lists. Without one, every
   topic you set is new, and they become the vocabulary: keep them few and plain.
4. **Each summary listed:** read the summary, its description and its body, not its notes.
   - Choose the topics its own text is about: at most five, the most specific that fit (a narrower
     topic rather than its broader one). A topic needs more than a passing word in the summary.
   - From the vocabulary first. A new topic only when nothing in it fits: a short lower-case name
     for a subject, a project or a kind of data, at most three new per file, and the same word for
     the same subject in every file of this run.
   - Run `labbrain topics --by <your actor> <summary> <topic>...`.
   - If it refuses a word (vetoed, or a fourth new one), choose from the vocabulary instead, or
     leave it out.
5. **Each other file listed:** read the file itself, and do the same. For a raw note, the command
   checks that its author allows agent metadata, and records you in its `annotated` entry.
6. **Files with vetoed topics:** set their topics again with `labbrain topics`, without the
   vetoed one; it replaces the old list.
7. **Bring the vocabulary up to date** with `labbrain vocabulary`: it adds the new topics you set
   to `topics.yaml`, and lists what waits for a person, such as a new topic spelled like another.
8. **Files no link reaches, and the proposed links** (curate's last two sections): list them for
   their authors. Add no link, and never run `labbrain reject`: turning a link down is a person's
   call.
9. **Bring the graph up to date** with `labbrain graph`, then run `labbrain check`: it must list no
   problem it didn't list before you started.
10. **Log and report.**
    - **Log:** in each repo where you set topics, a `log.md` entry under today's `## YYYY-MM-DD`
      heading: how many files got topics, and which new topics `labbrain vocabulary` added.
    - **Report** in chat: a table of the files and the topics set; then the new topics, and what
      `labbrain vocabulary` listed for review; then the files no link reaches and the proposed
      links.

## Rules
- **Topics come from `topics.yaml` first, and only through `labbrain topics`.** Never write
  `topics`, `annotated` or any header by hand.
- **Never edit `topics.yaml` or `labbrain.yaml` by hand.** `labbrain vocabulary` adds topics;
  synonyms, narrower topics, merges and vetoes are a person's.
- **A topic must be supported by the file's own text,** as a claim in a summary must be (see the
  `summary-writing` skill). No topic from general knowledge, and none for what the file only links
  to.
- **Never add a link** to a note, a summary or an `index.md` block, and never run
  `labbrain reject`. Code proposes links; people accept them or turn them down.
- **A raw note's text is never touched,** and its header only through `labbrain topics`, which
  refuses a note whose author hasn't allowed it.
- **Read only the files curate lists,** summaries first. Never read the whole wiki.

## Stop and ask
Stop, and wait for an answer, when:
- `labbrain stale` lists summaries, and running the `index` skill wasn't part of the request;
- a file's topics are unclear because its text points two ways.

Say what you found, the options and the one you recommend.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
