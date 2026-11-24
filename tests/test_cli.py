"""The CLI where it differs from okf_vault.sh: finding the vault, settings, required actors,
paths outside the vault, argparse."""

import pytest
from test_parity import snapshot

from labbrain.cli import COMMANDS, SETTINGS, BadSetting, find_vault, main, settings

BUNDLE = '---\nokf_version: "0.2"\n---\n'


def test_the_outermost_bundle_root_wins(tmp_path):
    """A wiki's sub-repos are bundles of their own, but the wiki is the outermost bundle root."""
    (tmp_path / "index.md").write_text(BUNDLE)
    sub = tmp_path / "Repo" / "Notes"
    sub.mkdir(parents=True)
    (tmp_path / "Repo" / "index.md").write_text(BUNDLE)
    assert find_vault(sub) == str(tmp_path)


def test_a_folder_index_is_not_a_root(tmp_path):
    wiki = tmp_path / "wiki"
    (wiki / "Notes").mkdir(parents=True)
    (wiki / "index.md").write_text(BUNDLE)
    (wiki / "Notes" / "index.md").write_text("# Notes\n")  # no okf_version: not a root
    assert find_vault(wiki / "Notes") == str(wiki)


def test_no_vault(tmp_path, monkeypatch, capsys):
    (tmp_path / ".obsidian").mkdir()  # an Obsidian vault is not a wiki until it declares OKF
    monkeypatch.chdir(tmp_path)
    assert find_vault(tmp_path) is None
    assert main(["check"]) == 2
    assert "no vault found" in capsys.readouterr().out


def test_a_vault_that_is_not_a_folder(tmp_path, capsys):
    """Walking a missing folder finds nothing to complain about, so check would say OK."""
    assert main(["check", "--vault", str(tmp_path / "gone")]) == 2
    assert "no such folder" in capsys.readouterr().out


def env_file(tmp_path, text):
    path = tmp_path / "settings.env"
    path.write_text(text)
    return path


def test_the_environment_wins_over_the_file(tmp_path):
    path = env_file(tmp_path, "LABBRAIN_CONTRIBUTOR=human:file\nLLM_MODEL=not-ours\n")
    assert settings({}, path) == {
        "LABBRAIN_CONTRIBUTOR": "human:file",
        "LABBRAIN_VAULT": None,
        "LABBRAIN_ANNOTATE": False,
    }
    got = settings({"LABBRAIN_CONTRIBUTOR": "human:shell"}, path)
    assert got["LABBRAIN_CONTRIBUTOR"] == "human:shell"
    assert settings({"LABBRAIN_CONTRIBUTOR": ""}, path)["LABBRAIN_CONTRIBUTOR"] == "human:file"
    assert settings({"LABBRAIN_ENV": str(path)})["LABBRAIN_CONTRIBUTOR"] == "human:file"
    assert settings({}, tmp_path / "none.env") == {
        **dict.fromkeys(SETTINGS),
        "LABBRAIN_ANNOTATE": False,
    }


def test_the_contributor_signs_new_notes(vault, git_env, monkeypatch, capsys):
    path = env_file(vault.parent, "LABBRAIN_CONTRIBUTOR=human:ada")
    monkeypatch.setenv("LABBRAIN_ENV", str(path))
    assert main(["frontmatter", "--vault", str(vault)]) == 0
    assert "generated: { by: human:ada }" in (vault / "Garden" / "Beans.md").read_text()
    assert main(["frontmatter", "--by", "human:bo", "--vault", str(vault)]) == 0  # nothing left
    (vault / "New.md").write_text("# New\n")
    assert main(["frontmatter", "--by", "human:bo", "--vault", str(vault)]) == 0
    assert "generated: { by: human:bo }" in (vault / "New.md").read_text()


def test_annotate_goes_only_on_your_own_notes(vault, git_env, monkeypatch):
    """Consent to agent metadata is the author's: written into notes signed as you, and never
    into a note whose header already answers."""
    path = env_file(vault.parent, "LABBRAIN_CONTRIBUTOR=human:ada\nLABBRAIN_ANNOTATE=true\n")
    monkeypatch.setenv("LABBRAIN_ENV", str(path))
    (vault / "Kitchen" / "Kept.md").write_text("---\nannotate: false\n---\n# Kept\n")
    assert main(["frontmatter", "--vault", str(vault)]) == 0
    beans = (vault / "Garden" / "Beans.md").read_text()
    assert beans.startswith("---\ntype: Note\ngenerated: { by: human:ada }\nannotate: true\n---\n")
    assert "annotate: true" in (vault / "Kitchen" / "Shopping.md").read_text()  # had a header
    assert "annotate: true" not in (vault / "Kitchen" / "Kept.md").read_text()
    (vault / "New.md").write_text("# New\n")
    assert main(["frontmatter", "--by", "human:bo", "--vault", str(vault)]) == 0
    assert "annotate" not in (vault / "New.md").read_text()


@pytest.mark.parametrize(
    "target", ["Garden/Beans.md", "Kitchen/Session_2026-01-05.md", "Garden/Nope_summary.md"]
)
def test_stamp_takes_only_folder_summaries(vault, git_env, monkeypatch, capsys, target):
    """A note would lose its author to the actor and gain the folder's sources. Nothing is
    written, not even the summary named before it."""
    monkeypatch.chdir(vault)
    before = snapshot(vault)
    args = ["stamp", "--by", "agent/test", "Garden/Garden_summary.md", target]
    assert main(args + ["--vault", str(vault)]) == 2
    assert capsys.readouterr().out == "not a folder summary, so not stamped: %s\n" % target
    assert snapshot(vault) == before


def test_the_vault_setting_is_only_a_fallback(vault, tmp_path, monkeypatch, capsys):
    other = tmp_path / "other"
    (other / "elsewhere").mkdir(parents=True)
    monkeypatch.setenv("LABBRAIN_VAULT", str(vault))
    monkeypatch.chdir(other / "elsewhere")
    assert main(["stale"]) == 1  # not inside a wiki: the setting's wiki, which has stale summaries
    (other / "index.md").write_text(BUNDLE)
    assert main(["stale"]) == 0  # inside a wiki: that one, which has none
    assert capsys.readouterr().out.endswith("0 stale summary(ies).\n")


@pytest.mark.parametrize(
    "environ, text",
    [
        ({"LABBRAIN_ENV": "{tmp}/missing.env"}, ""),
        ({}, "LABBRAIN_CONTRIBUTER=human:ada\n"),  # a typo
        ({}, "LABBRAIN_CONTRIBUTOR=ada\n"),
        ({}, "LABBRAIN_CONTRIBUTOR=human:ada@example.org\n"),
        ({"LABBRAIN_VAULT": "{tmp}/plain"}, ""),  # a folder, but not a wiki
        ({}, "LABBRAIN_CONTRIBUTOR=human:ada\nLABBRAIN_ANNOTATE=yes\n"),
        ({}, "LABBRAIN_ANNOTATE=true\n"),  # whose notes?
    ],
    ids=[
        "missing file",
        "unknown name",
        "not human:",
        "email",
        "not a wiki",
        "annotate not true or false",
        "annotate without a contributor",
    ],
)
def test_bad_settings_are_refused(tmp_path, monkeypatch, capsys, environ, text):
    environ = {k: v.replace("{tmp}", str(tmp_path)) for k, v in environ.items()}
    (tmp_path / "plain").mkdir()
    path = env_file(tmp_path, text)
    with pytest.raises(BadSetting):
        settings(environ, path)
    monkeypatch.setenv("LABBRAIN_ENV", environ.pop("LABBRAIN_ENV", str(path)))
    for k, v in environ.items():
        monkeypatch.setenv(k, v)
    (tmp_path / "index.md").write_text(BUNDLE)
    assert main(["check", "--vault", str(tmp_path)]) == 2
    assert capsys.readouterr().out.startswith("bad setting ")


def test_frontmatter_needs_an_actor(vault, git_env, capsys):
    """No default author: a wrong name written into every new note is worse than a refusal."""
    before = snapshot(vault)
    assert main(["frontmatter", "--vault", str(vault)]) == 2
    assert "usage: frontmatter --by ACTOR" in capsys.readouterr().out
    assert snapshot(vault) == before


@pytest.mark.parametrize(
    "args",
    [
        ("stamp", "--by", "agent/test", "Garden/Garden_summary.md", "{outside}"),
        ("links", "{outside}"),
        ("drift-stamp", "--by", "agent/test", "{outside}"),
        ("drift-stamp", "--by", "agent/test", "Garden/Tomatoes.md", "{outside}"),
    ],
    ids=["stamp", "links", "drift-stamp file", "drift-stamp summary"],
)
@pytest.mark.parametrize("how", ["relative", "absolute"])
def test_paths_outside_the_vault_are_refused(
    vault, tmp_path, git_env, monkeypatch, capsys, args, how
):
    """Nothing is written, inside the vault or outside it, even when a path before it is fine."""
    outside = tmp_path / "elsewhere_summary.md"
    outside.write_text("---\ntype: Folder Summary\n---\n# Elsewhere\n")
    monkeypatch.chdir(vault)
    path = "../elsewhere_summary.md" if how == "relative" else str(outside)
    before, outside_before = snapshot(vault), outside.read_text()
    assert main([a.replace("{outside}", path) for a in args] + ["--vault", str(vault)]) == 2
    assert "not inside the vault" in capsys.readouterr().out
    assert snapshot(vault) == before
    assert outside.read_text() == outside_before


def test_vault_before_or_after_the_command(vault, git_env, capsys):
    assert main(["--vault", str(vault), "stale"]) == 1
    first = capsys.readouterr().out
    assert main(["stale", "--vault", str(vault)]) == 1
    assert capsys.readouterr().out == first


def test_help_lists_every_command(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert all(c in out for c in COMMANDS)
    assert len(COMMANDS) == 9


def test_no_command(capsys):
    assert main([]) == 2
