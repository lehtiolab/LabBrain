# LabBrain docs

How LabBrain works, how to run it, and how to add to it. These guides are written for people and
agents alike: an agent working on this repo can load them as they are.

| guide | read it when |
|---|---|
| [How it works](how-it-works.md) | first: the wiki, the code, the models, and how a job runs |
| [Functions and skills](functions-and-skills.md) | you want to know what you can contribute, and which kind a job needs |
| [Writing a function](writing-a-function.md) | you're adding or changing the Python in `labbrain` |
| [Writing a skill](writing-a-skill.md) | you're adding or changing a `SKILL.md` |
| [Usage](usage.md) | you're running `labbrain`: every command, option, output and exit status |
| [Configuration](configuration.md) | you're setting up `env/.env` |

Two files hold rules rather than explanations:
- **[AGENT.md](../AGENT.md):** the rules for working on this repo. If a guide and AGENT.md
  disagree, AGENT.md is right and the guide needs fixing.
- **[skills/okf-conventions](../skills/okf-conventions/SKILL.md):** the rules a wiki follows.

There are no reference pages for individual functions yet, because the code is still moving. Until
then, the docstrings are the reference.

Keeping these guides true to the code is a job of its own, with its own skill:
[dev-skills/update-docs](../dev-skills/update-docs/SKILL.md).
