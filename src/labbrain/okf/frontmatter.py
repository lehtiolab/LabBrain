"""OKF frontmatter, parsed and written by hand so key order, flow mappings and quoting survive."""

import hashlib
import json
import re

FM_RE = re.compile(r"\A---[ \t]*\r?\n(?:(.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.S)


def split_fm(text):
    """(frontmatter text or None, body)."""
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1) or "", text[m.end() :]


def fm_blocks(fm):
    """Top-level keys of a frontmatter block, each with its raw lines, in order."""
    blocks = []
    for line in fm.split("\n"):
        m = re.match(r"([A-Za-z_][\w-]*)\s*:", line)
        if m:
            blocks.append([m.group(1), [line]])
        elif blocks:
            blocks[-1][1].append(line)
        else:
            blocks.append([None, [line]])
    return blocks


def unquote_yaml(v):
    v = v.strip()
    if v.startswith('"'):
        return json.loads(v)
    if v.startswith("'"):
        return v[1:-1].replace("''", "'")
    return v


def fm_get(fm, key):
    m = re.search(r"^%s\s*:[ \t]*(.*?)[ \t]*$" % re.escape(key), fm or "", re.M)
    return unquote_yaml(m.group(1)) if m and m.group(1) else None


def fm_list(fm, key):
    """A top-level list of scalars (block or flow style)."""
    for k, lines in fm_blocks(fm or ""):
        if k != key:
            continue
        head = lines[0].split(":", 1)[1].strip()
        if head.startswith("["):
            return [unquote_yaml(x) for x in head.strip("[]").split(",") if x.strip()]
        return [
            unquote_yaml(line.strip()[2:]) for line in lines[1:] if line.strip().startswith("- ")
        ]
    return []


SCALAR = r'("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'|[^,}]+?)'


SRC_FLOW = re.compile(r"^\s*-\s*\{\s*resource:\s*%s\s*,\s*hash:\s*([0-9a-f]{40})\s*\}\s*$" % SCALAR)


def fm_sources(fm):
    """[(resource, hash)] from a summary's `sources` block (flow or block entries)."""
    out, cur = [], None
    for k, lines in fm_blocks(fm or ""):
        if k != "sources":
            continue
        for line in lines[1:]:
            m = SRC_FLOW.match(line)
            if m:
                out.append((unquote_yaml(m.group(1)), m.group(2)))
                continue
            m = re.match(r"^\s*(-\s+)?(resource|hash)\s*:\s*(.+?)\s*$", line)
            if not m:
                continue
            if m.group(1):
                cur = {}
                out.append(cur)
            if cur is not None:
                cur[m.group(2)] = unquote_yaml(m.group(3))
    return [x if isinstance(x, tuple) else (x.get("resource"), x.get("hash")) for x in out]


FLOW_ITEM = re.compile(r"^\s*-\s*\{(.*)\}\s*$")


PAIR_RE = re.compile(r"(\w+)\s*:\s*%s\s*(?:,|$)" % SCALAR)


# A summary's record of when scan last checked it for drift against each file it hashes or cites.
DRIFT_KEY = "drift_verification"


def fm_drift(fm):
    """[{resource, hash, commit, at, by}] from a summary's drift_verification block."""
    for k, lines in fm_blocks(fm or ""):
        if k == DRIFT_KEY:
            items = (FLOW_ITEM.match(line) for line in lines[1:])
            return [
                {p.group(1): unquote_yaml(p.group(2)) for p in PAIR_RE.finditer(m.group(1).strip())}
                for m in items
                if m
            ]
    return []


def drift_lines(entries):
    """The drift_verification block: one flow mapping per file checked."""
    return ["%s:" % DRIFT_KEY] + [
        "  - { resource: %s, hash: %s, commit: %s, summary_hash: %s, at: %s, by: %s }"
        % (
            ys(e["resource"]),
            e["hash"],
            e.get("commit") or "none",
            e.get("summary_hash") or "none",
            e["at"],
            ys(e["by"]),
        )
        for e in entries
    ]


def content_hash(text):
    """What a summary says: a git-style hash of its description and body. Frontmatter bookkeeping
    (generated, sources, drift_verification) is left out, so only real edits change it."""
    fm, body = split_fm(text)
    data = ((fm_get(fm, "description") or "") + "\n" + body).encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def set_fm_block(text, key, lines, after=("verified", "generated")):
    """Replace a top-level frontmatter key, or insert it after the first `after` key present."""
    fm, body = split_fm(text)
    blocks = fm_blocks(fm or "")
    keys = [k for k, _ in blocks]
    anchor = None if key in keys else next((a for a in after if a in keys), None)
    out = []
    for k, ls in blocks:
        out += lines if k == key else ls
        if k == anchor:
            out += lines
    if key not in keys and anchor is None:
        out += lines
    return with_fm(out, body)


PLAIN = re.compile(r"[A-Za-z0-9_./~(-][A-Za-z0-9_ ./~@()':-]*")


def ys(s):
    """A YAML scalar: plain when unambiguous, otherwise double-quoted."""
    s = str(s)
    if (
        PLAIN.fullmatch(s)
        and not s.endswith((" ", ":"))
        and ": " not in s
        and s.lower() not in ("true", "false", "yes", "no", "on", "off", "null", "~")
        and not re.fullmatch(r"[\d.eE+:-]+", s)
    ):
        return s
    return json.dumps(s, ensure_ascii=False)


def with_fm(fm_lines, body, nl="\n"):
    return "---" + nl + nl.join(fm_lines) + nl + "---" + nl + body


def h1(body):
    m = re.search(r"^# (.+?)\s*$", body, re.M)
    return m.group(1) if m else None
