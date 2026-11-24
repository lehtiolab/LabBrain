---
date: 2026-11-24
title: The wiki's own config, the graph as a cache, code-first search, the graph page
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Work:** committed before this record, in fe38bd3, 542234b, d8698ab, 67647eb and 937fcab, on `feat/yaml-canvas`.

**Decided:**
- **Two levels of configuration** (fe38bd3). A person's settings stay in `env/.env`. Rules for
  everyone go in `labbrain.yaml` and `topics.yaml` at the wiki root, committed and changed by
  review; no setting overrides them. The vocabulary (topics, synonyms, narrower topics) is its own
  file, because it grows and changes often. Both are read once in `cli.py` and passed down field by
  field; a bad file stops every command.
- **The graph is a cache** (542234b): built by code from the wiki, never edited, never committed.
  Each markdown file is a node; `link`, `covers` and `child` are the edges. Sorted, with no times,
  so the same commits give the same bytes. A per-file cache keyed by git blob hash means a rebuild
  reads only changed files; links are resolved again on every run.
- **Search climbs a ladder with code only** (d8698ab): headers with the vocabulary, then the full
  text only if nothing was found (or `--text`), then links up to `--depth`, plus the summaries over
  what was found. The `search` skill runs it before a model reads anything.
- **The graph page** (67647eb, 937fcab): one HTML file with the graph inside and nothing loaded
  from elsewhere, so it works from disk or a server, without Obsidian. It opens at the wiki's root;
  a click re-centres it; a search puts its hits around the query. The layout is radial and
  deterministic. Three colours (summaries, notes, paper concepts) and grey for every other type,
  checked for colour-blind readers in light and dark, with summaries drawn larger so colour is never
  the only cue.

**Why:** the user wants to explore the wiki visually and filter what to see, to find the right
files without a model reading the whole wiki, and to run this for a lab on one shared repo, with a
graph agent curating it nightly. On the user's wiki (271 files, 818 links), a full build reads 261
files in under a second, and a rebuild with nothing changed reads none.

**Rejected:**
- **A second `.env` for the wiki:** flat lines can't hold a vocabulary, and `.env` is per person,
  ignored by git and the place for secrets.
- **Committing the graph:** one large file rewritten every night by several agents and people
  would conflict every day. Anyone rebuilds the same graph in seconds; the nightly run can publish a
  copy on the lab's server for people without LabBrain.
- **SQLite now:** the graph fits in memory, and the full-text step reads every file only when the
  headers find nothing. FTS5 is in both environments' SQLite for when that gets slow.

**Cost:**
- Search matches words, not meaning: the vocabulary has to carry the synonyms.
- Renaming a file changes its node's id; the graph agent will have to carry curated relations over.
- More than 350 files in view and the page cuts the outer rings.
- The graph agent, which curates topics and relations, is not started: it is on `feat/graph-agent`.
