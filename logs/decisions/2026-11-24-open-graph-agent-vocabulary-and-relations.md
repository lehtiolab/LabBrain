---
date: 2026-11-24
title: "Open: the graph agent waits for a vocabulary and a decision on relations"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Discovered:** the graph skill, tried on the author's wiki (85 summaries, 35 other agent-written
files that could take topics), can set nothing yet: the wiki has no `topics.yaml`. As the skill
says for that case, it drafted one for review: 37 topics with synonyms and narrower topics, from the
summaries' descriptions and the tags in use. The draft is in that wiki's
`_maps/topics-proposal.yaml`, on the author's machine only (git ignores `_maps/`).

**Open, for the user:**
1. **The vocabulary.** Review the draft, then commit it as `topics.yaml` at the wiki root; after
   that, running the graph skill sets topics on the files `labbrain curate` lists. The draft
   includes the lab's project names as topics, because they span several folders; they are also
   folder names, so they may be cut if topics should be subjects only.
2. **Where agent-proposed relations go.** The earlier design put them in `index.md` related blocks,
   but `summary-writing` forbids inferred connections and a related block holds the links notes ask
   for. Options:
   - (a) in the agent's report only, as now;
   - (b) saved in `_maps/` and shown as dashed "proposed" edges on the graph page, until an author
     accepts one by adding the link: recommended, since people see them while exploring and the
     wiki only records what authors linked;
   - (c) written into related blocks, marked as agent-proposed: changes a rule in okf-conventions.

**Cost:** until both are settled, no topics are set and relations are only proposed in reports.
