---
date: 2026-11-24
title: "The graph agent: code lists the work, the model picks topics, people decide what is new"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Decided:**
- **`labbrain curate` lists the graph agent's work, from the graph:** summaries, then other
  agent-written files and notes whose authors allow it, without topics; files whose topics aren't
  in the vocabulary; files no link reaches (for their authors); unused topics; the tags in use. It
  exits with 1 only when there is work and a vocabulary, so a nightly job stops before calling a
  model otherwise.
- **The `graph` skill is the job:** the model reads only the files curate lists, summaries first,
  and sets topics through `labbrain topics`. Without a vocabulary it drafts one, when asked, as
  `_maps/topics-proposal.yaml`, for a person to review and commit as `topics.yaml`.
- **New topics and relations between files are proposals in the report,** never written: not into
  `topics.yaml`, not as links, not into `index.md` related blocks.
- **Graph nodes carry `annotate: true`** where the author allows agent metadata, so curate works
  from the graph alone. The graph cache carries a version, and a cache from another version is
  rebuilt rather than misread.

**Why:** the user wants a graph agent that curates the graph nightly, like the drift and index jobs,
and searching that stays cheap. Code decides what runs; the model reads only what code lists.

**Rejected:**
- **The model growing the vocabulary itself:** free tags drift; the user's wiki already has 38
  tags on 22 files, most used once.
- **Writing agent-proposed relations into `related` blocks,** which the earlier design allowed:
  `summary-writing` forbids inferred connections, and a related block holds the links notes ask
  for. Left for the user to decide.

**Cost:** relations aren't curated yet, only proposed. The job runs by hand until the night-run
dispatcher exists. The files no link reaches are only reported.
