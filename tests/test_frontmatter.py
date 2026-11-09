"""The hand-written frontmatter parser, on the shapes stamp never writes but humans do."""

from labbrain.okf.frontmatter import (
    content_hash,
    fm_drift,
    fm_get,
    fm_list,
    fm_sources,
    set_fm_block,
    split_fm,
    ys,
)

HASH = "a" * 40


def test_split():
    assert split_fm("# No frontmatter\n") == (None, "# No frontmatter\n")
    assert split_fm("---\n---\nbody") == ("", "body")
    assert split_fm("---\r\ntype: Note\r\n---\r\nbody") == ("type: Note", "body")


def test_scalars_and_lists():
    fm = "title: \"A: b\"\nquote: 'it''s'\ntags: [one, two]\nchildren:\n  - a.md\n  - b.md"
    assert fm_get(fm, "title") == "A: b"
    assert fm_get(fm, "quote") == "it's"
    assert fm_get(fm, "missing") is None
    assert fm_list(fm, "tags") == ["one", "two"]
    assert fm_list(fm, "children") == ["a.md", "b.md"]


def test_sources_flow_and_block():
    fm = (
        "sources:\n"
        f"  - {{ resource: Flow.md, hash: {HASH} }}\n"
        f'  - {{ resource: "With space.md", hash: {HASH} }}\n'
        "  - resource: Block.md\n"
        f"    hash: {HASH}\n"
        "other: x"
    )
    assert fm_sources(fm) == [("Flow.md", HASH), ("With space.md", HASH), ("Block.md", HASH)]


def test_drift_entries():
    fm = (
        "drift_verification:\n"
        f"  - {{ resource: A.md, hash: {HASH}, commit: abc1234, summary_hash: {HASH}, "
        "at: 2026-01-01T00:00:00Z, by: agent/test }"
    )
    [e] = fm_drift(fm)
    assert e == {
        "resource": "A.md",
        "hash": HASH,
        "commit": "abc1234",
        "summary_hash": HASH,
        "at": "2026-01-01T00:00:00Z",
        "by": "agent/test",
    }


def test_ys_quotes_only_when_needed():
    assert ys("plain/path.md") == "plain/path.md"
    for s in ("yes", "a: b", "12", "trailing ", "#hash"):
        assert ys(s).startswith('"'), s


def test_set_block_replaces_or_inserts_after_anchor():
    text = "---\ntype: X\ngenerated: { by: a }\ntitle: T\n---\nbody"
    inserted = set_fm_block(text, "drift_verification", ["drift_verification: []"])
    assert inserted.split("\n")[3] == "drift_verification: []"
    assert set_fm_block(inserted, "drift_verification", ["drift_verification:"]).count("drift") == 1


def test_content_hash_ignores_bookkeeping():
    a = "---\ndescription: D\ngenerated: { by: a }\n---\nbody"
    b = "---\ndescription: D\ngenerated: { by: b, at: now }\n---\nbody"
    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash(a.replace("body", "body!"))
