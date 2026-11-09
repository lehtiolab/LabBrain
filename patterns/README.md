# patterns/: what the agents learn from their runs

> **Draft.** No code writes or reads these files yet. The formats are here so the first job that
> records a run, and the first skill-proposer job, start from the same shape.

This is the WikiSkills loop (arXiv 2608.27454), in two kinds of file:
- **Traces:** what ran, with which skill, and how it came out. They are never edited.
- **Patterns:** what worked and what failed, drawn from many traces. A maintainer job writes them,
  and a skill-proposer job reads them when it suggests changes to `skills/`.

**Where the files live:**
- **In this repo:** the formats, and dummy examples in `examples/`.
- **In each wiki:** real traces in `patterns/traces/`, and its patterns as `patterns/*.md`.

**Real traces never come back to this repo, because they contain the lab's data.** `.gitignore`
blocks `patterns/traces/` here. A pattern that holds beyond one lab can come back by pull request,
rewritten without that lab's data, the same way an evolved skill does.

## Traces
Traces are JSON lines, one file per day: `patterns/traces/YYYY-MM-DD.jsonl`. A record is appended
and never rewritten, so a truncated write costs one record. Feedback arrives later as a record of its own.

```json
{"id": "2026-01-05T03:00:12Z-index-1", "at": "2026-01-05T03:00:12Z", "job": "index", "skill": "index", "skill_version": "<git blob hash of SKILL.md>", "skill_by": "claude-code/claude-opus-5-5", "actor": "open-llm/qwen3-235b", "labbrain": "0.1.0", "inputs": [{"resource": "Garden/Tomatoes.md", "hash": "<blob>"}], "steps": [{"run": "labbrain stale", "exit": 1}, {"model": "rebuild Garden/Garden_summary.md", "attempts": 1}, {"run": "labbrain check", "exit": 0}], "outcome": "pass", "problems": []}
{"feedback_for": "2026-01-05T03:00:12Z-index-1", "at": "2026-01-06T09:14:00Z", "by": "human:<name>", "score": 4, "comment": "<what was good or wrong>"}
```

| field | what it holds |
|---|---|
| `id` | unique within the wiki: time, job and a counter |
| `job`, `skill` | the job that ran, and the skill it followed |
| `skill_version` | the git blob hash of the `SKILL.md` it followed, so a change to the skill can be told apart from a change to the model |
| `skill_by`, `actor` | which model wrote that skill version, and which model ran it. A skill written by a large model may be beyond a small one. |
| `labbrain` | the package version |
| `inputs` | the files the run read, with their blob hashes, so the exact versions can be recovered |
| `steps` | each command and its exit status, and each model call and how many attempts it took |
| `outcome`, `problems` | `pass` or `fail`, and what the code checks found |
| `feedback_for` | a later record: a person's score (1–5) and comment on a run |

For search, a trace also records the question, which step answered it (keyword, one model call, or
the search loop) and whether the person found what they needed. This is the search log that shows
when a RAG index is worth building.

## Patterns
Each pattern is one markdown file, with OKF frontmatter, in the wiki's `patterns/`:

```yaml
---
type: Pattern
title: "<what happens, in a few words>"
description: "<one sentence: the failure or success, and when it happens>"
skills: [index]
status: proposed          # proposed → accepted → retired
evidence:                 # the traces it is drawn from
  - 2026-01-05T03:00:12Z-index-1
generated: { by: <actor>, at: <YYYY-MM-DDTHH:MM:SSZ> }
---
```

The body has three sections: *What happens*, *Why*, *What to do instead*. A pattern is only as
strong as its evidence, so every claim names the traces behind it.
