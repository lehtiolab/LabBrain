---
name: drift
description: Check that folder summaries still say what their notes say, starting with the notes that change most (a drift scan). Use when asked to scan, check for drift or verify summaries, after the index skill has run. labbrain finds the hot files and the summaries that are due, and the model rebuilds blind and compares claim by claim. The same steps also run unattended as a nightly job.
---

# drift: check summaries against the notes that change most

## Why
`labbrain stale` catches a summary whose notes changed after it was built. It can't catch
**meaning drift:** a summary that is current by hash but no longer says what its notes say. This
happens in three ways:
- every rebuild edits the previous summary, so mistakes add up, as in a game of telephone;
- a re-stamp after a link-only edit can hide a real change;
- a description or a map entry falls behind.

Drift builds up where notes change most, so this job checks those first.

## When
Run it after `index` (if `labbrain stale` lists anything, run the `index` skill first), and nightly
once the summaries have been rebuilt. A checked summary is checked again only when the file and the
summary have changed 3 times between them since the last check, not on every scan.

## Code versus model
| step | done by |
|---|---|
| which files are hot, which files cite them, which summaries are due | code: `labbrain hot` |
| a blind rebuild of what the summaries should say | **the model** |
| the claim-by-claim comparison, and the fixes | **the model** |
| recording the check | code: `labbrain drift-stamp` |

The nightly job makes these two separate model calls. The blind rebuild never sees the current
summary, so it can't copy that summary's mistakes.

## Steps
1. **Make the hashes current first.** If `labbrain stale` lists anything, run the `index` skill first.
2. **Find what is due** with `labbrain hot`.
   - **Hot:** a file with at least 3 changes in the last 30 days, counting commits plus one for
     uncommitted edits. `--min N --days D` change the threshold and the window, and `--recheck R`
     changes when a checked summary becomes due again.
   - **What it lists:** for each hot file, the summary that hashes it and every agent-written file
     that links to it, with the file marked `DUE` or `skip: checked`.
   - **Session summaries** are records, so they are never checked. **Map and related blocks** carry
     no record of a check, so they are checked whenever their hot file is.

   If nothing is due, say so and stop.
3. **Rebuild blind.** For each due hot file, read the current file in full. Then, without looking at
   the existing summaries, write down what they should say about it: its purpose, current state, key
   points, open questions, and a one-line description.
4. **Compare claim by claim** with each due summary, and with every map or related block that
   `hot` lists for that file. Flag:
   - *lost:* something important in the blind version is missing from the summary, such as a new
     decision, a changed status, or new or ticked tasks;
   - *unsupported:* the file no longer supports a claim, because it was removed or contradicted, or
     its numbers, names or dates are out of date;
   - *flipped:* a qualifier or position was reversed, softened or hardened;
   - *wrong citation:* a `[Note § Heading]` link whose heading is gone or says something else;
   - *stale description:* the Contents line, the summary's `description` or the map entry no longer fits.
5. **Fix what is clearly wrong,** in agent-written files only, following `summary-writing`. A
   summary whose sources didn't change is edited in place, not re-stamped. If a `description`
   changed, run `labbrain index`.
6. **Leave judgement to the author.** If two notes disagree, if it's unclear whether the author
   changed position, or if a fix would need an inferred connection, don't edit. Stop and ask instead.
7. **Record the checks.** After the fixes, run `labbrain drift-stamp --by <your actor> <hot file>`
   for each hot file you checked.
   - It writes the entry in every summary that was due for that file. The entry holds the summary's
     hash after your fixes, so the fixes don't count as edits.
   - Don't record a check on a summary while a question about it is still open. Once it is settled,
     name the summary: `labbrain drift-stamp --by <actor> <hot file> <summary>...`.
   - Don't also run `labbrain stamp` on the summary: the check doesn't change its sources.
8. **Log and report.**
   - **Log:** add a `log.md` entry in each repo you touched. Give the window and thresholds, the
     files checked, the files skipped (with the date of their last check), what drifted and what
     was fixed.
   - **Report:** a table in chat with the file, its changes, the files checked, and a verdict: no
     drift, fixed (what), for the author (what), or skipped.
   - **Check:** `labbrain check` must end with `OK`.
9. **Commit.** `labbrain commit --by <your actor> -m "drift: <what was checked>"`. Never push: a
   person does that.

## Stop and ask
Stop, and don't start the next step, whenever a fix needs the author's judgement (step 6), or the
request is ambiguous. Say what you found, the options and the one you recommend, then wait for an answer.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
