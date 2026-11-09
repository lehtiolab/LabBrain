# Functions and skills

There are two kinds of thing you can contribute to LabBrain, and most jobs need both.

## A function
A function is Python code in `src/labbrain/okf/`. It does one mechanical thing: it takes the wiki's
folder and whatever else it needs, and returns data. The `labbrain` commands are thin wrappers that
call functions and print what they return.

For example, `labbrain stale` calls `staleness(vault, summary)` for every summary. The function
compares the hashes the summary recorded with the files on disk, and returns a list such as
`[("new", "Fresh.md"), ("changed", "Tomatoes.md")]`.

A function:
- needs no model, and gives the same answer every time for the same files;
- is tested: pytest runs it on a dummy wiki;
- never prints, never reads settings itself, and never decides what runs next. It is told.

## A skill
A skill is a markdown file, `skills/<name>/SKILL.md`, that an LLM reads before it does a job. It is
instructions in plain language: why the job exists, when to run it, which `labbrain` commands to
run, what the model writes itself, and when to stop and ask a person.

For example, the `summary-writing` skill tells a model how to rebuild a folder summary. It says to
write only what the notes say, to link every claim to its note and heading, and to keep the author's
qualifiers. When the text is done, it says to run `labbrain stamp`.

A skill:
- is for the steps that need reading and judgement;
- works with any LLM: nothing in it is tied to one tool;
- is tested only for its form (its frontmatter, and whether the commands it names exist). Whether it
  works is found out by running it.

## The difference
| | function | skill |
|---|---|---|
| is | Python, in `src/labbrain/okf/` | markdown, in `skills/<name>/SKILL.md` |
| run by | the computer, through `labbrain <command>` | an LLM, which reads it and follows it |
| does | what can be worked out from names, paths, dates, git hashes or fixed text | what needs a note read: writing, comparing, judging |
| gives | the same answer every time | an answer that varies with the model, and needs checking |
| costs | nothing | tokens |
| checked by | unit tests, and parity tests against the original script | `tests/test_skills.py` for its form; a trial run on a wiki for its content |
| lives | here; every wiki runs the same code | here as a seed; each wiki keeps and evolves its own copy |

## How they fit together
A skill calls functions through `labbrain` commands. The `index` skill, for example, has the model
run `labbrain stale` (code finds the stale summaries), rebuild each summary (the model writes), and
then run `labbrain stamp` (code records the hashes). Each job skill has a *Code versus model* table
that says which step is which.

The rule is: **if code can work a value out, code writes it.** The skill tells the model to run the
command, never to write the value by hand. A model copying 40-character hashes will get one wrong
sooner or later; `labbrain stamp` never does.

## Which one do I need?
Ask this of each step of the job:
1. **Can it be worked out from file names, paths, dates, hashes or fixed text?** Then it is a
   function, and perhaps a command.
2. **Does it need a note read, or a judgement made?** Then it is a step in a skill.
3. **Does it decide what runs, or which files may change?** Then it is code, never a model.

| you want | write |
|---|---|
| `check` to flag a summary that has no description | a function, in `check.py` |
| summaries to spell out an acronym the first time it appears | a line in the `summary-writing` skill |
| a job that drafts concepts from a published paper | a skill for the reading, and functions for the file names and headers it creates |
| a list of the notes nobody has edited in a year | a function and a command; no model is needed |

Next: [Writing a function](writing-a-function.md), or [Writing a skill](writing-a-skill.md).
