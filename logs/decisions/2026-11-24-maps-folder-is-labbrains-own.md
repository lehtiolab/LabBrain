---
date: 2026-11-24
title: _maps/ at the wiki root is labbrain's own
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Work:** committed before this record, in d9c41ef, on `feat/yaml-canvas`.

**Discovered:** a git-ignored folder isn't invisible to labbrain. `listdir` skips only dot-names,
so pictures in an ignored `maps/` would still become summary sources, need headers and show up in
listings.

**Decided:** `listdir` skips `_maps/` at the wiki root, so no command sees it. The picture commands
write `_maps/.gitignore` with `*`, so the folder ignores itself, and a wiki's own `.gitignore` is
never touched. `test_the_maps_folder_is_invisible` holds this against the reference script.

**Why:** the user wanted the pictures inside the wiki and ignored by git, to try them out.

**Rejected:**
- **`maps/`:** a lab's own `maps/` folder (genetic maps, site maps) would silently drop out of its
  summaries.
- **A dot-folder:** Obsidian hides it, so the canvas couldn't be opened.
- **Making `walk` honour `.gitignore`:** the wiki's root ignores `Shelf/`-style sub-repos that must
  still be walked, and it would change every command.

**Cost:** a wiki that has its own `_maps/` at the root loses it from summaries and listings.
