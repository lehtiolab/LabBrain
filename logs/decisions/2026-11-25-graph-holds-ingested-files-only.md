---
date: 2026-11-25
title: "The graph holds ingested files only: a header with a type, listed in their folder's index.md"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
---

**Decided:**
- **A file is a node only when it is ingested:** its header has a `type`, and the `index.md` of its
  own folder lists it. The test is per file. A link from another folder's `index.md`, such as the
  map or a related block, doesn't count.
- **The others are the graph's `waiting` list.** `labbrain graph` prints them, and `search` and
  `curate` say how many they left out. No edge leads to them, so `search`, `curate` and the page
  never see them.
- **Each `index.md` is cached by its git blob hash,** like the notes, so a rebuild with nothing
  changed still reads no file.

**Why:** the user wants curate and the graph agent to work only on files that are ready. Tried on
a real wiki, the files no link reached were new notes that weren't ingested yet. The user chose
`index.md` as the test, over the summary.

**Rejected:**
- **"Passes `labbrain check`":** check also flags topics outside the vocabulary, and fixing those
  is curate's job.
- **"The folder summary records this version of the file":** a note would drop out of the graph and
  search after any edit, until a model rebuilt its summary.
- **Testing a whole folder:** one new note would hide every file beside it.
- **Keeping the files in the graph, marked and skipped by curate:** the user chose to leave them
  out.

**Cost:**
- `search` and the graph page can't find a note until `frontmatter` and `index` have run.
- A stale summary is still in the graph, and curate still lists it for topics.
- A wiki where `labbrain index` never ran has an empty graph; the command says how many files wait.
