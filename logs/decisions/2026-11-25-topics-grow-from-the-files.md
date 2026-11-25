---
date: 2026-11-25
title: "Topics grow from the files: a few new ones per file, added to topics.yaml for people to review"
decided_by: [human:patrickCNMartin, claude-code/claude-opus-5-5]
supersedes: 2026-11-24-topics-written-by-code.md
---

**Decided:**
- **`labbrain topics` takes new words.** A word that names a topic in `topics.yaml`, or one of its
  synonyms, is written as that topic. Any other word is a new topic, written in lower case with
  hyphens, and used straight away. At most 3 of a file's topics may be new. A vetoed topic is
  refused.
- **`labbrain vocabulary` is the mapping tool.** It adds each topic in use that `topics.yaml`
  doesn't name to the end of the file, with `status: new`. It never rewrites what is already
  there. It then lists what waits for a person: new topics, spellings close to another topic, and
  vetoed topics still on files.
- **People review in `topics.yaml`:** keep a topic (delete `status: new`), merge it into another
  (make it one of its synonyms), or veto it (`status: vetoed`). A merge rewrites no file: the graph
  maps each file's topics through the vocabulary. Proposed links leave vetoed topics out.
- **`check` flags topics in use that `topics.yaml` doesn't list (run: vocabulary), and vetoed
  topics on files.** `curate` lists the files with vetoed topics for the agent, and the new topics
  for people. It no longer needs a vocabulary to find work.
- **The skills:** `summary-writing` and `graph` choose from the vocabulary first, and the `index`
  and `graph` skills run `labbrain vocabulary`. The graph skill no longer drafts a vocabulary.

**Why:** a vocabulary that only a person can grow is too static for a knowledge base that keeps
changing: new projects and new kinds of data must not wait for someone to edit a file. The user
wants evolution, with its variation, and wants it auditable: each topic on a file is written by an
actor; each topic that enters the vocabulary arrives in a commit; each merge, narrower topic and
veto is a person's edit. Review never blocks use.

**Rejected:**
- **The fixed vocabulary of 2026-11-24-topics-written-by-code.md:** every new subject waited for a
  person, and the proposals were lost in chat reports.
- **Free tags with no vocabulary,** rejected again from 2026-11-24-graph-agent-job.md: they drift.
  Choosing from the vocabulary first, the 3-new limit, and the spelling check are what keep this
  design from drifting the same way.
- **Working out the topic list from the files on each run, with `topics.yaml` holding only
  relations:** less code, but no single list to read, and no history of when each topic came in.
- **Holding a new topic back until it is reviewed:** too slow for a wiki that keeps growing.
- **Semantic embeddings, to find synonyms and merges:** possible later, as a layer that proposes
  merges for people; code and the vocabulary stay the record.

**Cost:**
- The spelling check catches variants (`vegetable` and `vegetables`), but not words that mean the
  same thing (`lfq` and `label-free`). Those need a person, or a model later.
- Two branches that both add topics both append to the end of `topics.yaml`, so their merge
  conflicts.
- The 3-new limit is a fixed number in the code, not a wiki setting.
- A `topics.yaml` written before statuses existed has none, so all its topics count as reviewed.
