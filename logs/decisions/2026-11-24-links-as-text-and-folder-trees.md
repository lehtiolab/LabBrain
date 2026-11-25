---
date: 2026-11-24
title: Links as text, a folder's own tree, _maps/ at every repo root
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Work:** committed before this record, in ef72b7d, 8c50ebd and 0d70251, on `feat/yaml-canvas`.

**Decided:**
- **A box's links are one line of text,** `→ Vision — Summary · Nix — Summary`, each name a link to
  its file, not arrows (ef72b7d). A name is the file's `title`, else its file name. The extra boxes
  for files no summary covers went with the arrows.
- **`labbrain hierarchy FOLDER...` draws one part of the wiki** into `_maps/<FOLDER>/`. The tree's
  top is the folder's own summary when everything else in it sits under that summary, else the
  folder itself. Links that leave the folder stay, to show how it connects to the rest.
- **`_maps/` is skipped at the root of every git repo in the wiki** (8c50ebd), not only at the
  wiki's root.

**Why:**
- On the user's wiki, 246 link arrows crossed whole columns of boxes. Leaving out links along a
  branch would have removed only 14 of them. The user chose links as text over hiding them until
  hover, or keeping only the links between bundles.
- The user expects people to ask for a picture of one directory, not only of the whole wiki.
- `--vault` can name an inner bundle, which puts `_maps/` in that bundle's root. A later run on the
  whole wiki would then have taken the pictures for the bundle summary's sources.

**Cost:**
- Links no longer show where their target sits in the picture; the name says which summary it is.
- Links to images and PDFs show like any other file a summary links to.
