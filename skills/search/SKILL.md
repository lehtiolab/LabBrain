---
name: search
description: Find things in an OKF lab wiki and answer questions from it, without changing any file. Use when someone asks what the wiki says about a topic, project, method, dataset or person, or where something lives. Reads cheapest first (index.md listings, then folder summaries, then raw notes) and cites the notes it used.
---

# Search an OKF wiki

The wiki is a folder of markdown notes in the Open Knowledge Format (OKF v0.2), kept in git. People
write the raw notes; agents and code write the folder summaries and the `index.md` listings that
make the notes findable. The `okf-conventions` skill has the rules behind them.

**This skill only reads.** Don't edit any file, not even to fix a broken link or a stale summary.
Report what you found; maintenance belongs to the `index` and `drift` skills.

## Read cheapest first
1. **The request names a file or folder:** go straight there and skip the map.
2. **Otherwise start at the root `index.md`.** Its listing, and its map between `<!-- map:start -->`
   and `<!-- map:end -->`, say where each topic, project and person lives.
3. **Then the folder's `index.md`:** a generated listing with one line per note. The line is
   often enough to pick the one note to open.
4. **Then the folder summary** (`<Folder>_summary.md`). It covers every note in the folder, and in
   any subfolder without a summary of its own. Each claim links to the note and heading it comes from.
5. **A raw note only when the summary isn't enough,** or when the answer matters enough to check.

Searching by keyword (grep) over titles, headings, and the descriptions in `index.md` files is cheap,
so do it before reading whole notes. A hit can look relevant and still not answer the question, so
read it before you answer.

## Trust, and when to check
- **A summary is agent-written:** it is a map to the notes, not a source. When an answer rests on
  one claim, follow the claim's link and read that section of the note.
- **Check that a summary is current** before relying on it. `labbrain stale` lists summaries whose
  notes changed since they were built. If the folder you need is listed, read the changed notes.
- **Code repos are the source of truth for code.** A summary with `code_repo` and `repo_commit`
  describes the repo at that commit. Check the repo if it has moved on.
- **Many notes are stubs:** a link to a note doesn't mean the note has content.
- **Raw notes are informal:** spelling varies, and positions are often hedged. Report what the
  author says, qualifiers included. Don't make a hedged view sound settled, or a settled one hedged.

## Answering
- Cite every claim with a relative link to the note and heading: `[Note § Heading](Folder/Note.md#Heading)`.
- Keep what the notes say apart from what you infer, and label your inferences.
- If the wiki doesn't answer the question, say so, and say where you looked. If you fill the gap
  from general knowledge, say that is what you did.
- If you noticed a problem on the way (a summary that contradicts its note, a broken link, a stale
  summary), mention it at the end.

## Stop and ask
Stop and ask before going on when the question is ambiguous, or when the notes disagree and the
answer depends on which one is right. Give what you found, the options, and the one you would pick.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
