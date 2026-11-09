---
type: Pattern
title: "Citations to headings that don't exist"
description: "A small model rebuilding a summary cites a heading it expects a note to have rather than one it has; the citation check catches it."
skills: [index, summary-writing]
status: proposed
evidence:
  - 2026-01-05T03:00:12Z-index-1
  - 2026-01-05T03:04:40Z-index-2
generated: { by: agent/test, at: 2026-01-07T03:00:00Z }
---
# Citations to headings that don't exist

## What happens
Two rebuilds cited a heading that their note does not have (`#Harvest`, `#Sauces`). One fixed it on
the retry; one failed both attempts.

## Why
Both notes have short, informal headings. The model wrote the heading it expected a note on that
subject to have.

## What to do instead
Proposed change to `summary-writing`: list the note's actual headings in the prompt, and ask for
citations to be copied from that list.
