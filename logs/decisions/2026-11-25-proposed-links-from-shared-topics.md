---
date: 2026-11-25
title: "Proposed links: code finds them from shared topics, the page dashes them, people turn them down"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
supersedes: 2026-11-24-open-graph-agent-vocabulary-and-relations.md
---

**Decided:**
- **The graph proposes links, with code only:** two ingested files that share two topics or more,
  with no edge between them, and neither in the other's folder. They are edges of kind `proposed`,
  rebuilt with the graph like every other edge.
- **The graph page draws them dashed,** with a checkbox of their own, and its side panel lists the
  ones of the file in the middle with the topics both files have. `curate` lists them for their
  authors.
- **An author accepts one by adding the link,** and the proposal goes. **A person turns one down
  with `labbrain reject --by human:<name> FILE FILE`:** an agent's actor is refused, and so is a
  pair the graph doesn't propose.
- **Rejections go in `_maps/rejected.jsonl`,** one line each, added and never rewritten. A line the
  graph can't read stops every command that builds it. They move to `patterns/` later, beside the
  traces of runs: a rejection is feedback on a proposal.
- **The graph skill no longer collects relations the model notices.** It lists the proposed links
  for their authors and never runs `reject`.
- **Finding relations that aren't obvious is on the wish list** in AGENT.md, with `llm()` and the
  night run.

**Why:** the user chose option (b), dashed proposed edges on the page, and code-only pairs for now,
to keep the graph simple. Proposals are an overlay on the same nodes. Code-only pairs can be
rebuilt like the graph. Model proposals could only be made again, at a cost and with a different
result. Rejections can't be rebuilt at all: nothing in the wiki records them.

**Rejected:**
- **(a) proposals in the agent's report only:** nobody sees them while exploring.
- **(c) agent-proposed entries in `index.md` related blocks:** `summary-writing` forbids inferred
  connections, and a related block holds the links notes ask for.
- **The model's proposals now:** a whole-wiki pass grows with the square of the files (a wiki of
  270 files has about 36,000 pairs), and code has to pick the candidates first.
- **`labbrain propose --reject`:** with code making the proposals, `propose` alone would do
  nothing.

**Cost:**
- Nothing is proposed until files have topics.
- Topics match by name only, so narrower topics don't count. A file at the wiki's root is never
  proposed, because the root holds every folder.
- Rejections are kept per machine, and lost if `_maps/` is thrown away. Renaming a file can bring a
  rejected link back.
- `reject` doesn't redraw the page; `labbrain graph` does.
