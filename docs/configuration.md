# Configuration

Settings about you, not about the wiki, go in `env/.env`. labbrain works without any of them; they
save you typing the same thing on every run.

## Setting up
```sh
cp env/.env.example env/.env
```
Then fill in the values you want. `env/.env` is ignored by git. `env/.env.example` is the tracked
template: it lists every setting, each one empty, so a copy you forget to edit changes nothing.

## The settings
| setting | what it's for | example |
|---|---|---|
| `LABBRAIN_CONTRIBUTOR` | you, as an actor: the default for `labbrain frontmatter --by` | `human:ada` |
| `LABBRAIN_VAULT` | the wiki to use when you run labbrain outside any wiki | `~/wiki` |
| `LABBRAIN_ANNOTATE` | whether agents may add metadata to the header of your notes: `true` or `false` (the default) | `true` |
| `LABBRAIN_ENV` | where your settings file is, if not `env/.env`. Set it in your shell, not in the file | `~/.config/labbrain.env` |

**`LABBRAIN_CONTRIBUTOR`** is written as `human:<name>`, with no spaces and no email address. It is
only a default for `frontmatter`, which signs every new note it finds with it. `stamp` and
`drift-stamp` never use it, because their actor must name the model that did the work.
On a shared wiki, `frontmatter` also signs notes other people wrote, so pass `--by` explicitly when
the new notes aren't all yours.

**`LABBRAIN_VAULT`** is the root of a wiki: a folder whose `index.md` declares `okf_version`, given
as an absolute path or one starting with `~`. It is used only when you're outside every wiki and
didn't pass `--vault`. The wiki you're standing in always wins, so an out-of-date setting can't send
changes to the wrong wiki.

**`LABBRAIN_ANNOTATE`** is your answer to one question: may agents add metadata, such as a
`description`, to the header of your notes? Your notes' text is never touched either way.
- **It is recorded in each note, not read from your settings later.** When `labbrain frontmatter`
  gives a new note its header, and the note is signed as you (`LABBRAIN_CONTRIBUTOR`), it also writes
  `annotate: true`. Agents read the note's header, never the settings of whoever runs them, so
  someone else's job can't decide for your notes.
- **No setting, no settings file, or `false` means no:** the key isn't written, and a note without it
  is never annotated.
- **It applies to new notes only.** A note that already has a header keeps it; to change your answer
  for a note, add or remove `annotate: true` in its header by hand.
- **A note signed as someone else** (`frontmatter --by human:ali`) never gets your answer.
- What an agent adds is recorded in the note's `annotated` key (see the
  [okf-conventions](../skills/okf-conventions/SKILL.md) skill). No labbrain command adds agent
  metadata yet.

## Where labbrain looks
For each setting, the first of these that has a value wins:
1. the option on the command line (`--by`, `--vault`);
2. the variable in your shell's environment, if it's set and not empty;
3. the settings file: the file `LABBRAIN_ENV` names, or else `env/.env` in the LabBrain checkout
   that labbrain runs from.

For the wiki there is one more step, between 1 and 2: the wiki you're in (see
[Finding the wiki](usage.md#finding-the-wiki)).

**A labbrain installed as a package,** rather than run from a checkout, has no `env/.env`. Set
`LABBRAIN_ENV`, or the variables themselves.

**For a scheduled job,** set the variables in the job's environment, or point `LABBRAIN_ENV` at a
file kept for that job.

## Mistakes it refuses
labbrain stops before doing anything, prints `bad setting …` and exits with 2, when:
- `LABBRAIN_ENV` names a file that doesn't exist;
- the settings file has a name starting with `LABBRAIN_` that labbrain doesn't know, which is usually
  a typo;
- `LABBRAIN_CONTRIBUTOR` isn't `human:<name>`, or contains an email address;
- `LABBRAIN_VAULT` isn't the root of a wiki;
- `LABBRAIN_ANNOTATE` isn't `true` or `false`, or is `true` without a `LABBRAIN_CONTRIBUTOR` to say
  whose notes it is about.

Names that don't start with `LABBRAIN_` are ignored, so the file can hold other tools' settings too.

## What isn't a setting
- **The agent actor** for `stamp` and `drift-stamp`. It has to name the model that actually did the
  work, and a default would be wrong the first time you switched tools.
- **`hot`'s thresholds** (`--days`, `--min`, `--recheck`) **and the note types.** These are rules for
  the whole wiki. If each person set their own, "checked for drift" would mean something different
  depending on who ran the check. Change them for one run with the options.

## Coming later
With the code that calls a model (`llm()`), the settings file will also hold:
- the model, and where to reach it: an OpenAI-compatible URL, a model name and an API key;
- the path to your own agent preferences: how you like answers given to you.

They aren't in `env/.env.example` yet, because no code reads them.

## Secrets
Once models are configured, `env/.env` will hold an API key. It is ignored by git, and
`detect-secrets` checks every push once the pre-commit hook is installed (see the README). Never
put a real value in `env/.env.example`.
