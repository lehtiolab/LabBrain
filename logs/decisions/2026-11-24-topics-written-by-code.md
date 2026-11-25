---
date: 2026-11-24
title: Topics come from the vocabulary and are written by code
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Decided:**
- **`labbrain topics --by ACTOR FILE TOPIC...` writes a file's `topics`.** The model chooses them;
  the command checks each against `topics.yaml` (a synonym names its topic), and writes nothing if
  any word names no topic. A new topic is for a person to add, by review.
- **Where:** a folder summary (in its canonical key order, `topics` after `tags`), another
  agent-written file, or a raw note whose header says `annotate: true`. On a raw note, `topics`
  goes after the author's own keys, with ACTOR's entry in `annotated`; the note's text is never
  touched. Any other file is refused.
- **`check` flags a topic that isn't in the vocabulary.** A deliberate difference from
  `okf_vault.sh`, which has no vocabulary.
- **The summary-writing skill sets topics after `stamp`,** so a rebuilt summary's topics are as
  fresh as its text. The graph agent fills in the rest.

**Why:** the graph agent curates the wiki's topics, and the user agreed they go on summaries, and on
notes only with their author's consent. okf-conventions already said agent metadata would be
written by code with the model supplying only the value; this is the first command that does it.

**Rejected:**
- **Topics written by hand, like `description`:** nothing would check them until `check` ran, and a
  raw note would get no `annotated` record.
- **Topics on any note:** consent is the author's, recorded in the note, never decided by whoever
  runs the job.

**Cost:** a summary's topics don't record who chose them or when; its `generated` covers the
summary as a whole. A raw note with CRLF line ends gets an LF header.
