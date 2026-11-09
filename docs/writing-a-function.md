# Writing a function

How to add to, or change, the Python in LabBrain. [AGENT.md](../AGENT.md) holds the rules; this
guide explains them, with an example.

## Before you write anything
Climb this ladder, and stop at the first rung that holds:
1. Does this need to exist at all?
2. Is it already in this repo? Search `src/labbrain/okf/` first: most of what a wiki needs is a
   combination of what is already there.
3. Does the standard library do it?
4. Can it be one line?

Read the whole path your change touches before you start, and fix a bug where it starts, not where
it shows up.

## Where it goes
There is one module per subject, in `src/labbrain/okf/`:

| module | holds |
|---|---|
| `files.py` | reading, writing and walking the wiki's files; which files count as text |
| `frontmatter.py` | the hand-written frontmatter parser and writer |
| `git.py` | every call to git: blob hashes, history, the repos inside the wiki |
| `summaries.py` | what a summary should record, staleness, and stamping |
| `notes.py` | raw notes: the minimal header, the concept types, which files are agent-written |
| `links.py` | wikilinks, broken links, and carrying hashes past link-only edits |
| `index.py` | the generated `index.md` listings |
| `drift.py` | hot files and drift checks |
| `check.py` | `check`: every conformance test at once |

`src/labbrain/cli.py` is the command line. It reads the settings, finds the wiki, calls functions
and prints their results. Nothing else prints.

## The rules
- **Everything a function needs comes in as an argument:** the wiki's folder (`vault`), and
  whatever else it uses. It doesn't read `os.environ`, the settings or the working directory: the
  settings are read once, in `cli.py`, and passed down. A long list of arguments is fine, because
  it shows what the function uses.
- **Return data; don't print.** `cli.py` decides what the person sees.
- **Nothing is kept between calls.** A cache is created by the function that needs it and passed
  down, as in `history(vault, rel, cache)`. The nightly run will be one process running many jobs,
  and a cache kept in the module would serve history from before the latest commit.
- **Paths are relative to the wiki's root,** such as `Garden/Tomatoes.md`. Build them with
  `files.join`, and read and write with `files.read` and `files.write`.
- **A raw note's text is never rewritten.** `convert_links` rewrites its link syntax, and
  `add_frontmatter` adds its header. Any other metadata goes into a note's header only when the
  header says `annotate: true`, with an entry in `annotated`, and never replaces `generated`. Other
  output goes to summaries, `index.md` blocks or logs.
- **Frontmatter goes through `frontmatter.py`.** There is no YAML library on purpose: one would
  reorder keys and change quoting.
- **Git goes through `git.py`.**
- **An error is an exception that takes data.** Arguments in, attributes stored, and the message
  formatted in `__init__`:
  ```python
  class OutsideVault(Exception):
      """A file argument that resolves to a path outside the vault."""

      def __init__(self, path, vault):
          self.path, self.vault = path, vault
          super().__init__("not inside the vault %s: %s" % (vault, path))
  ```
- **A one-line docstring,** and comments only where the code isn't obvious.
- **No new dependency without a reason,** written in the audit log. The runtime today is the
  standard library plus `python-dotenv`.

## An example
Say `check` should flag a folder summary that has no `description`, since `index.md` shows the
description next to the folder. *(This is an example; it isn't in the code.)*

The test comes first, in `tests/test_check.py`. The `vault` fixture is a fresh copy of the dummy wiki,
with its git history, and `git_env` gives git a dummy identity:
```python
from labbrain.okf.check import check


def test_a_summary_needs_a_description(vault, git_env):
    path = vault / "Garden" / "Soil" / "Soil_summary.md"
    path.write_text(path.read_text().replace("description:", "summary:", 1))
    assert ("Garden/Soil/Soil_summary.md", "no description") in check(str(vault))
```
Then the code, in the loop over summaries in `check.py`:
```python
        if not fm_get(split_fm(read(vault, s))[0], "description"):
            problems.append((s, "no description"))
```
Then run the whole suite. The parity tests compare `check` with the original script on the dummy
wiki. Its summaries all have a description, so they still pass. If they didn't, see
[Changing behaviour on purpose](#changing-behaviour-on-purpose).

## Making it a command
A new command, or a new option, goes in `cli.py`:
1. a line in `COMMANDS`, which is also its `--help` text;
2. its arguments in `parser()`;
3. a branch in `main()` that calls the function and prints the result. File arguments arrive already
   checked, as wiki-relative paths, in `rest`.

The exit status is 0 when there was nothing wrong, 1 when the command found something, and 2 when it
couldn't run.

Then the docs: a section in [usage.md](usage.md), a row in the README's command table, and a row in
the `okf-conventions` skill's table. `tests/test_docs.py` fails until `usage.md` names the command
and each of its options.

## Tests
- **pytest,** with these fixtures from `tests/conftest.py`:
  - `vault`: a fresh copy of the dummy wiki, with git history. `conftest.py` says what's in it;
  - `git_env`: a dummy git identity and no global git config, for in-process calls;
  - `tmp_path`, pytest's own, for anything else.
- **A test never writes into the repo, never calls a live model, and never reads your `env/.env`.**
- **Dummy data only:** the garden and the kitchen. No real notes, names or lab data, ever.
- **A case the dummy wiki doesn't cover** goes into `tests/fixtures/vault/`, and is named in
  `test_reference_sees_the_fixture`, so the test fails loudly if the fixture ever stops reaching it.

## Changing behaviour on purpose
`tests/reference/okf_vault.sh` is the original script. `tests/test_parity.py` runs it next to the
package on copies of the same wiki, and expects the same output and the same files. If your change
alters what a command prints or writes on the dummy wiki:
- change `test_parity.py` in the same commit;
- add the difference to AGENT.md's list of known differences;
- add an entry to `logs/audit_log.md` that says why.

## Before you push
```sh
pixi run -e dev test
pixi run -e py311 test   # the oldest Python we support
pixi run -e dev lint
```
