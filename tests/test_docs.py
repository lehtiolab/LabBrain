"""The docs name every command, option and setting the code has, and their links lead somewhere."""

import argparse
import re
from pathlib import Path
from urllib.parse import unquote

import pytest
from dotenv import dotenv_values

from labbrain.cli import SETTINGS, parser
from labbrain.okf.links import MDLINK_RE, outside_code

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
SHARED = {"-h", "--help", "--vault"}  # documented once, not under each command


def commands():
    """{command: its options}, read from the parser itself."""
    sub = next(a for a in parser()._actions if isinstance(a, argparse._SubParsersAction))
    return {
        name: {o for a in p._actions for o in a.option_strings} - SHARED
        for name, p in sub.choices.items()
    }


def test_usage_documents_every_command_and_option():
    """Each command has a `### labbrain <command>` section, which names each of its options."""
    text = (DOCS / "usage.md").read_text(encoding="utf-8")
    sections = dict(re.findall(r"^### labbrain ([a-z-]+)\n(.*?)(?=^#{1,3} |\Z)", text, re.M | re.S))
    assert sorted(commands()) == sorted(sections)
    for name, opts in commands().items():
        assert {o for o in opts if o not in sections[name]} == set(), name
    assert "--vault" in text


def test_the_example_settings_file():
    """Every setting, each one empty, so a copy nobody edited changes nothing."""
    example = dotenv_values(ROOT / "env" / ".env.example")
    assert list(example) == list(SETTINGS)
    assert set(example.values()) == {""}


def test_configuration_documents_every_setting():
    text = (DOCS / "configuration.md").read_text(encoding="utf-8")
    assert [s for s in SETTINGS + ("LABBRAIN_ENV",) if s not in text] == []


def test_the_docs_index_lists_every_guide():
    text = (DOCS / "README.md").read_text(encoding="utf-8")
    assert [p.name for p in DOCS.glob("*.md") if "](%s)" % p.name not in text] == ["README.md"]


PAGES = [ROOT / "README.md", *sorted(DOCS.glob("*.md")), *sorted(ROOT.glob("dev-skills/*/*.md"))]


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_lead_somewhere(page):
    broken = []

    def scan(s):
        for m in MDLINK_RE.finditer(s):
            url = m.group(3)
            if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I) or url.startswith("#"):
                continue
            if not (page.parent / unquote(url.partition("#")[0])).exists():
                broken.append(url)
        return s

    outside_code(page.read_text(encoding="utf-8"), scan)
    assert broken == []
