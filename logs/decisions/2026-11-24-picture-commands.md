---
date: 2026-11-24
title: "Pictures: one tree layout, two views, summaries as the tree"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Work:** committed before this record, in ea57af9, 05aacac and 7f269fc, on `feat/yaml-canvas`.

**Decided:**
- `labbrain canvas` draws any JSON or YAML file and `labbrain hierarchy` draws the folder
  summaries, both into `_maps/`. Both are experimental.
- **One layout, two views:** an Obsidian canvas or a self-contained web page, chosen by `--view`
  or the person's `LABBRAIN_VIEW`.
- **Boxes are text, with the title linking to the file,** not canvas file nodes. Run on a test
  file, a file node showed the file but dropped the box's title and description.
- **The tree is worked out from the folders on disk,** with `expected()`, not from the `parent` and
  `children` recorded in frontmatter, which can be out of date.
- **A link to a note becomes a link to the summary that covers it** (`covers()`). Links to the
  summary's own notes, its parent and its children are left out, since the tree shows them.
- **The web page draws arrows above the boxes,** so an arrow crossing a box can't pass for a link
  from it.

**Why:** the user wanted to see the subjects and their relationships before paying a model to read
the summaries. Everything here can be worked out from paths, frontmatter and links, so it is code.

**Cost:**
- On the user's wiki (85 summaries, 246 links between them), the tree reads well, but the link
  arrows tangle: they cross whole columns of boxes. How to show links is open.
- Subjects inside the summaries, which need a model, are not started.
