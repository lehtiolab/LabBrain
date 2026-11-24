---
name: graph
description: Curate the wiki's graph, the graph agent's job. Give folder summaries, other agent-written files and the notes whose authors allow it topics from the wiki's vocabulary (topics.yaml), so that code-only search finds files by subject without a model reading the wiki. Use when asked to curate the graph, tag files, add topics or draft a vocabulary, and as a nightly job after the index skill. labbrain curate lists the work; the model reads only those files and sets topics with labbrain topics; new topics and relations between files are proposals for a person, never written. Experimental.
---

# graph: curate the wiki's topics

## Why
`labbrain search` and the graph page find files by their headers first: title, description, path,
tags and topics. That costs nothing, but only if the headers say what the files are about. A
summary's `topics`, taken from the wiki's vocabulary, do that for its whole folder: a search for
"tumour" finds the summaries about cancer without a model reading a single note.

The vocabulary is the lab's, in `topics.yaml` at the wiki root. Free tags drift as soon as several
people write them, so this job only ever picks topics from that list. A new topic is a proposal for
a person.

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
| which files need topics, which topics are unknown, which files no link reaches | code: `labbrain curate` |
| reading a listed file and choosing its topics from the vocabulary | **the model** |
| checking the topics against the vocabulary, and writing them | code: `labbrain topics` |
| a raw note: whether its author allows it, and the `annotated` record | code: `labbrain topics` |
| new topics, relations between files | **the model** proposes; a person decides |
| bringing the graph up to date | code: `labbrain graph` |

## Steps
1. **Check the summaries are current** with `labbrain stale`. If it lists anything, run the `index`
   skill first.
2. **List the work** with `labbrain curate`. If it says `nothing for the graph agent to do` and
   there is a vocabulary, stop.
3. **No vocabulary yet** (curate says so first): draft one for a person, only if you were asked to.
   - Start from what curate prints: the summaries' titles and descriptions, and the tags in use.
   - Write it as `_maps/topics-proposal.yaml`, in the format of `topics.yaml` (see
     `docs/configuration.md`): a short lower-case name per topic, the synonyms the notes actually
     use, and narrower topics. Ten to thirty topics, the subjects the lab works on, not every word.
   - Never write `topics.yaml` itself. Stop and ask: a person reviews the draft and commits it.
4. **Each summary listed:** read the summary, its description and its body, not its notes.
   - Choose the topics its own text is about: at most five, the most specific that fit (a narrower
     topic rather than its broader one). A topic needs more than a passing word in the summary.
   - Run `labbrain topics --by <your actor> <summary> <topic>...`.
   - If it refuses a word, use the vocabulary's own word for it, or leave it out. If no topic fits,
     set none, and note the words the summary would need (step 7).
5. **Each other file listed:** read the file itself, and do the same. For a raw note, the command
   checks that its author allows agent metadata, and records you in its `annotated` entry.
6. **Files with topics not in topics.yaml:** set their topics again with `labbrain topics`, using
   words from the vocabulary; it replaces the old list. If nothing in the vocabulary fits, leave the
   file as it is and add the word to the proposals (step 7).
7. **Collect proposals for a person,** without acting on them:
   - **a new topic:** the word, the synonyms you saw, the files that need it, and a short quote
     from one that shows it;
   - **a relation** you noticed between two files that no link records ("this note uses that
     method"): both files, and what each says. A link is its author's to add.
8. **Files no link reaches** (curate's last section): list them for their authors. Add nothing.
9. **Bring the graph up to date** with `labbrain graph`, then run `labbrain check`: it must list no
   problem it didn't list before you started.
10. **Log and report.**
    - **Log:** in each repo where you set topics, a `log.md` entry under today's `## YYYY-MM-DD`
      heading: how many files got topics, and how many proposals wait for a person.
    - **Report** in chat: a table of the files and the topics set; then the proposals; then the
      files no link reaches.

## Rules
- **Topics come only from `topics.yaml`, and only through `labbrain topics`.** Never write `topics`,
  `annotated` or any header by hand.
- **Never edit `topics.yaml` or `labbrain.yaml`.** They are the lab's, changed by review.
- **A topic must be supported by the file's own text,** as a claim in a summary must be (see the
  `summary-writing` skill). No topic from general knowledge, and none for what the file only links
  to.
- **Never add a link or a relation** to a note, a summary or an `index.md` block. Relations are
  proposals in your report.
- **A raw note's text is never touched,** and its header only through `labbrain topics`, which
  refuses a note whose author hasn't allowed it.
- **Read only the files curate lists,** summaries first. Never read the whole wiki.

## Stop and ask
Stop, and wait for an answer, when:
- `labbrain stale` lists summaries, and running the `index` skill wasn't part of the request;
- there is no vocabulary: after drafting one, if you were asked to;
- you have proposals: new topics or relations;
- a file's topics are unclear because its text points two ways.

Say what you found, the options and the one you recommend.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
