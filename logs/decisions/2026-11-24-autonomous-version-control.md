---
date: 2026-11-24
title: Version control is autonomous, on GitHub and on the wiki
decided_by: [human:AHTARazzak, claude-code/claude-opus-5-5]
---

**Decided:**
- **`labbrain commit` (05901f9) is the local primitive:** each job commits its own work once
  `check` passes, and never pushes. It is not the version-control agent.
- **The version-control agent is autonomous at two levels:** a GitHub bot for LabBrain's code, and
  an async queued worker for the wiki's repos. Routine progression waits for no person.
- **GitHub is the code host.** The bot may update branches, open and update PRs, and merge once
  required checks pass. It flags what it can't safely reconcile.
- **Wiki intake starts on a shared VM/environment.**
- **A conflict outside the defined rules stops and is flagged.** Human-authored notes stay protected.

**Why:** the team's meeting notes say the version-control agent tracks changes "with no humans
needed", and propose a GitHub Action that harmonizes conflicts before merging. The earlier rule,
"agents commit, people push" (09 Nov, on this branch only, never merged), covered only the first
slice and contradicted the notes. Rejected: a person pushing every run, and leaving the code
repository out of scope.

**Cost:** nothing autonomous is built yet; `docs/version-control-agent.md` holds the design and
what is still open. The bot's workflow will change two AGENT.md rules (read-only CI token, agents
never push) when it lands.
