---
name: paper-ingest
description: Draft OKF concepts from one published paper (PDF) into a lab wiki, as a paper folder of Paper, Method, Finding and Dataset files that answer the lab's general questions. Use when asked to add, ingest, import or summarize a paper into the wiki. Everything it writes stays a draft until a person checks it against the paper.
---

# paper-ingest: add a published paper to the wiki

## Why
Lab members ask questions across many papers: which data a study used, what it found, how a
method works. Reading the PDFs each time is slow, and a search over raw PDFs misses structure.
A paper folder breaks one paper into small concept files, each saying what the paper says and
pointing to where it says it, so search can answer from the right file and cite it.

## When
Run it when a person gives you a paper PDF to add. Before writing anything, search the wiki for the
paper's DOI (`git grep -n "<doi>"` in each repo). If a file already names it, the paper is in the
wiki: stop and ask whether to update that folder or leave it.

## Code versus model
| step | done by |
|---|---|
| the paper folder's path | **the model, for now**, by the naming rule below; a labbrain command will take this over |
| each file's header (`type`, `title`, `description`, `status`, `generated`, `sources`) | **the model, for now**, from the template below; a labbrain command will take over everything but `title` and `description` |
| the text of every concept | **the model** |
| the `index.md` listings | code: `labbrain index` |
| the parent summary, the map and the log entry | the `index` skill |
| conformance | code: `labbrain check` |

## The paper folder
- **Path:** `papers/<first author's surname>-<year>-<short name>/`, all lowercase, hyphens for
  spaces, letters and digits only, e.g. `papers/zhu-2020-deqms/`. If the wiki keeps papers
  somewhere else, or `papers/` doesn't exist, stop and ask.
- **Files,** all in that one folder, no subfolders:

| file | type | holds |
|---|---|---|
| `paper.md` | `Paper` | the citation, a short summary and the general questions (below) |
| `method-<name>.md` | `Method` or `Algorithm` | one method the paper introduces or relies on; key equations in plain text; a software package the paper releases goes here too |
| `finding-<name>.md` | `Finding` | one result: the claim, its numbers, its caveats, and the datasets it used |
| `dataset-<accession or name>.md` | `Dataset` | samples, design, sizes, accession, repository |

Name files after what they hold, lowercase with hyphens: `finding-spike-in-benchmark.md`,
`dataset-pxd013276.md`. Write only these four kinds of file. Don't copy the PDF into the wiki: the DOI is the source.

## The header of every file
```yaml
---
type: Finding
title: "<what it is, in a few words>"
description: "<one sentence with the specifics: method, organism, sample, quantification, accession, headline number>"
status: draft
generated: { by: <your actor>, at: <YYYY-MM-DDTHH:MM:SSZ> }
sources:
  - { id: paper, resource: https://doi.org/<doi> }
---
```
- `index.md` shows the `description` next to the file, and search reads it first. Make it carry
  the words a person would search for.
- Get the time from `date -u +%Y-%m-%dT%H:%M:%SZ`. Your actor is `<tool>/<model>` (see
  `okf-conventions`).
- `paper.md` also carries the citation: `authors`, `journal`, `year`, `volume`, `pages`, `doi`, and
  `pmid`, `pmcid` and `license` when the paper prints them.
- Never add `verified`. Only a person who has checked the file against the paper adds it.

## paper.md
After the header, these sections, in this order:
1. `## Summary`: two or three sentences on what the paper contributes.
2. `## General questions`, with exactly these four questions as `###` headings, word for word and
   in this order, so that answers can be compared across papers:
   - `### What problem does the paper address?`
   - `### What methods/algorithms does the paper use?`
   - `### What data does it use?`
   - `### What is the main result?`

   Answer each in one to three sentences, with the specifics (methods, organisms, sample types,
   cell lines, quantification, accessions, headline numbers), and link the concept files that hold
   the details. If the paper doesn't say, write that it doesn't say.
3. `## Contents`: one line per file in the folder, `- [Title](file.md) — what it is`.

## Steps
1. **Check the paper isn't in the wiki** (When, above).
2. **Read the whole paper,** including figure legends, tables, methods and data availability. Plan
   the files: one per method, finding and dataset that a lab member might ask about.
3. **Create the folder** and write `paper.md` first, then the other files.
4. **Re-read your files against the paper.** Check every number, accession and name. Remove what
   you can't find in the paper.
5. **Listings:** `labbrain index`. It writes the paper folder's `index.md` from your titles and
   descriptions.
6. **Run the `index` skill.** The summary of the folder that holds `papers/` is now stale, and the
   map and the log need the new paper.
7. **Check:** `labbrain check` must end with `OK`. Fix what it points to before you report.

## Rules
- **Only what the paper says.** No general knowledge, no numbers or accessions from memory, no
  conclusions the authors didn't draw.
- **Cite where it says it.** Attribute numbers and claims with a footnote keyed to the source:
  `201 proteins.[^fig3]` and `[^fig3]: Zhu et al. 2020, Results, Fig. 3A.`
- **Say when a number comes from a figure** rather than the text: "(read from Fig. 3A)".
- **Keep the authors' hedges.** "Suggests" stays "suggests".
- **Relative links only:** `[spike-in benchmark](finding-spike-in-benchmark.md)`, or
  `../other-paper/paper.md` across papers. Never a link that starts with `/`.
- **Write only inside the new paper folder.** Everything outside it changes through `labbrain`
  commands and the `index` skill.

## Stop and ask
Stop, and don't start the next step, when:
- the paper, or a file naming its DOI, is already in the wiki;
- the wiki has no `papers/` folder, or keeps papers elsewhere;
- you can't read the PDF properly (a scan, missing pages, text out of order);
- the paper is unpublished, a preprint the person may not mean to add, or marked confidential;
- the main results are only in supplementary files you weren't given.

Say what you found, the options and the one you recommend, then wait for an answer.

## Running labbrain
Run `labbrain <command>` from the wiki root, or from anywhere with `--vault <wiki root>`. File
arguments are relative to where you run it, and must be inside the wiki. If `labbrain` isn't on your
PATH, stay in the wiki and run it through a LabBrain checkout:
`pixi run --manifest-path <LabBrain>/pixi.toml labbrain <command>`, or
`uv run --project <LabBrain> labbrain <command>`.
