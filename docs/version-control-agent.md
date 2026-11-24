# Version control agent: design direction

## Purpose

The version-control work should automate version harmonization at two levels:

1. **LabBrain code contributions on GitHub:** agents help developers prepare, check, harmonize and
   progress code changes through the branch and merge workflow.
2. **The lab wiki graph:** an async worker tracks and harmonizes concurrent changes to the wiki's
   markdown repositories, which live outside the LabBrain code repository.

The meeting notes make the autonomy goal clear: the version-control agent should track changes
“with no humans needed,” and the later notes call for an agent that autonomously harmonizes work as
developers contribute. Routine work should progress without a person pushing or approving every
run. The system should preserve provenance, keep changes attributable, detect incompatible edits,
and make a bad version recoverable. It should escalate work when its rules cannot safely proceed.

## Decided

- **Code host:** GitHub.
- **GitHub bot authority:** the bot may update branches, open and update PRs, and merge a PR once
  its required checks pass. It flags a change it cannot safely reconcile instead of merging it.
- **Wiki intake:** contributors start on a shared VM/environment.
- **Conflicts:** the worker stops and flags any conflict outside its defined rules. Agents never
  rewrite the text of a human-authored note.

## Shared deterministic core

Code should own Git mechanics and enforce policy. It should provide repeatable operations to inspect
repository state, capture and compare versions, detect stale bases, record provenance, validate
changes, and apply an allowed transition. It should make file scope, branch policy, credentials,
locking, retries, and recovery explicit. Models can explain a conflict or propose a bounded edit;
they should not invent hashes, choose unrestricted paths, or run unbounded Git operations.

Git blob and commit IDs already identify file contents and repository history. A future version
record should build on those identities rather than create a competing hash scheme. It could link a
run ID to input versions, output commits, actor or worker, time, job/skill version, validation result,
and recovery status. Choose stored fields when a concrete workflow needs them.

The wiki may span several Git repositories. The core should connect each repository's commit to one
run/version record and report partial progress, since Git cannot commit changes atomically across
repositories.

## Level 1: GitHub code contribution workflow

The audit/conflict work described in the notes can run as a GitHub Action on proposed code changes.
It should combine deterministic checks for code hygiene and branch state with an agent review for
conflicts that require understanding context. The automation updates a branch, opens or updates a
PR, and merges a change once required checks pass. This fills gaps in ordinary GitHub collaboration
and systematizes development practices across contributors.

Today's CI (`.github/workflows/ci.yml`) is read-only: it runs tests, ruff and secret checks with
`contents: read`, on `pull_request`, with checkout credentials disabled. The bot needs its own
workflow, a separately scoped identity, and write permissions. That workflow should run write steps
only after validating the event and target branch, never run a fork's code with write access, and
leave a clear failure when a repair or merge is unsafe. It changes two AGENT.md rules, which say the
CI token is read-only and agents never push, so those rules change in the same PR as the workflow.

## Level 2: async wiki graph worker

The wiki worker should repeatedly inspect a durable queue of incoming changes, take one work item
under a lock, compare its recorded base with the current wiki version, and run the right checks or
specialist job. It should be idempotent: retrying a failed step must not duplicate a commit or lose
the original input. It records progress and leaves a clear failure item when it cannot safely
continue.

An expected path is:

1. Capture the incoming version and its parent/base.
2. Run deterministic hygiene and structural checks.
3. Detect overlap with changes that arrived since that base.
4. Reconcile automatically where explicit, testable rules apply. Use a model to explain or propose a
   semantic resolution when needed; validate the proposal with code.
5. Run the relevant audit, drift and wiki checks against the resulting graph.
6. Record the output version and advance it under the agreed branch policy, or flag the blocked item.

The queue implementation and scheduling mechanism are open. A queue could start as a durable
directory/database-backed work list in the shared environment; it must survive process restarts and
support concurrent workers.

## Specialist jobs and boundaries

| responsibility | purpose | likely trigger | model role |
|---|---|---|---|
| GitHub audit/conflict | Harmonize code contributions and identify incompatible changes before merge | GitHub Action on a proposed change | Review context, explain conflicts, and propose bounded repairs |
| Wiki audit/conflict | Find incompatible or contradictory knowledge and flag or propose harmonization | Queued or scheduled wiki audit | Compare meaning and explain conflicts |
| Drift | Check whether summaries and indexes still represent their source notes and graph | Async scheduled or change-triggered job | Compare semantics and revise agent-written summaries |
| Version worker | Coordinate queue, version records, repository operations, retries and progression | GitHub workflow or async worker loop | Interpret only bounded ambiguous cases |

The diagram's “Conflict” label describes the rationale for audit. Git merge conflicts, semantic
contradictions in wiki content, stale summaries, and code hygiene failures are distinct conditions.
The worker should report them separately and apply only the resolution rules for that condition.
Human-authored raw wiki notes remain protected by the existing LabBrain rule that agents do not
rewrite their text.

## Contributor and wiki editing workflows

The code contribution workflow is GitHub-based, but the wiki graph is separate. The meeting notes
say wiki markdown belongs in a common location outside the LabBrain code repository, for privacy and
to avoid stale links when the code repository is cloned.

Wiki edits start on a shared VM/environment with an intake-to-production flow. People edit a
mounted working copy, Git provides durable history, and an intake branch feeds a `production`
branch. Every change needs a recorded base version so concurrent edits can be detected, and the
worker needs a lock or an isolated worktree per task. Personal clones or PRs to the wiki's remote
could come later through the same queue and validation flow.

## Still open

- **Required checks:** which checks gate a bot merge, and whether any paths always need a person.
- **Wiki branches:** are `main` and `production` the branch names and meanings for all wikis?
- **Wiki identity:** where do wiki remotes live, who owns the bot credentials, and how are they
  stored outside the repository?
- **Conflict rules:** the defined rules for each kind of conflict; anything outside them is
  flagged.
- **Queue/version record:** where do durable work items live, and what is the minimum useful
  progression record?
- **Multi-repository recovery:** what should happen if one repository advances but another fails?

## Rollout

1. Keep `labbrain commit` as the local wiki commit primitive; it currently runs `check` and stops
   before fetch, push, queueing, reconciliation or merge.
2. Define narrowly scoped GitHub bot permissions for branch, PR and merge actions.
3. Specify the wiki branches, queue item, version record, locks, retries, and partial
   multi-repository failure behavior.
4. Add deterministic status, compare and validation operations before autonomous reconciliation.
5. Build the GitHub action and wiki worker as separate workflows over the shared deterministic
   operations; keep code review and semantic wiki audit as distinct jobs.
6. Enable automatic progression for transitions with clear validation and recovery rules; flag the
   rest with enough context to resolve them.
