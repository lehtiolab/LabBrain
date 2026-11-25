---
date: 2026-11-24
title: PyYAML is a runtime dependency
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Work:** committed before this record, in 67de892, on `feat/yaml-canvas`.

**Decided:** PyYAML joins the runtime, beside `python-dotenv`. It reads and writes whole YAML data
files, and reads with `safe_load` only. Frontmatter stays with the hand-written parser.

**Why:** the user asked for pictures of any JSON or YAML file, and expects YAML to be needed for
other jobs later. The rule against a YAML library was about rewriting frontmatter, where key order
and quoting must survive; a whole data file read once has no such need. PyYAML was already in both
locks, through pre-commit.

**Rejected:**
- **JSON only, or YAML only in the subset the frontmatter parser reads:** neither reads any YAML file.

**Cost:** a compiled dependency, with wheels for every platform pixi lists.
