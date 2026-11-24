---
name: canvas
description: Draw the wiki's folder summaries as one tree, with the links between them, or draw any JSON or YAML file as a tree of boxes, as an Obsidian canvas or a web page. Use when asked for a map, picture, canvas, diagram, overview or hierarchy of the wiki or of its subjects, or to see how a JSON or YAML file nests. Code does all the drawing; the model runs the commands, checks the result and reports what it shows. Experimental.
---

# canvas: draw the wiki's summaries, or any JSON or YAML file

## Why
A wiki with many folders is hard to see whole. Its summaries already know which folder sits under
which and what they link to, so code can draw that without reading a note. The same drawing works
for any JSON or YAML file, to see how its data nests.

This is experimental: the point is to find out whether the picture is useful. Report what looks
wrong or cluttered, and change nothing to make the picture look better.

## When
- **When someone asks** for a map, picture, canvas, overview or hierarchy of the wiki, or of a JSON
  or YAML file in it.
- **The picture is only as current as the summaries.** Run `labbrain stale` first. If it lists
  anything, say so before drawing; offer the `index` skill to bring the summaries up to date.

## Code versus model
| step | done by |
|---|---|
| which summaries are stale | code: `labbrain stale` |
| the tree of summaries and their links | code: `labbrain hierarchy` |
| the picture of any JSON or YAML file | code: `labbrain canvas` |
| where the files go | code: always `_maps/` at the wiki root, at the path of what was drawn |
| reading the result, and the report | **the model** |

No step needs a note read. Never write the tree, a link or a picture by hand.

## Steps
1. **Check the summaries** with `labbrain stale`. If any are stale, say which, and ask whether to
   go on or to run the `index` skill first.
2. **Draw.**
   - The wiki's summaries: `labbrain hierarchy`. It writes `_maps/hierarchy.yaml` and its picture.
   - One part of the wiki: `labbrain hierarchy <folder>`, with the folder the person named. It
     writes `_maps/<folder>/hierarchy.yaml` and its picture. Links that leave the folder stay, so
     the picture shows how that part connects to the rest.
   - A JSON or YAML file: `labbrain canvas <file>`.
   - The picture is an Obsidian canvas unless the person's `LABBRAIN_VIEW` says `html`. Add
     `--view html` or `--view canvas` only if they ask for that view.
3. **Read the result.** For the summaries, read the `hierarchy.yaml` that step 2 wrote. Look for:
   - summaries with no `description`: their boxes show a title only;
   - links to notes rather than summaries, because no summary covers them: a folder that may
     need a summary;
   - a summary that links to many others, or that nothing links to.
4. **Report** in chat: the path of the picture to open, the number of summaries and links, and what
   you saw in step 3. Say what you saw, not what it means for the notes: that is for their authors.

## Rules
- **Write nothing but through `labbrain hierarchy` and `labbrain canvas`.** They write only in
  `_maps/`, which git ignores and no other command reads.
- **Never edit a file in `_maps/` by hand.** Every run rewrites it.
- **Don't fix the wiki to improve the picture.** A missing description or a stray link is a finding
  to report. Fixing it is a job for the `index` or `drift` skill, and only if asked.

## Stop and ask
Stop, and wait for an answer, when:
- `labbrain stale` lists summaries (step 1);
- the file to draw isn't in the wiki, or isn't JSON or YAML: `labbrain canvas` refuses it;
- the request is to draw the subjects inside the summaries rather than the summaries themselves.
  That needs a model to read the summaries, and isn't built yet.

Say what you found, the options and the one you recommend.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
