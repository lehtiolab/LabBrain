#!/bin/sh
# okf_vault.sh: keep the vault conformant with OKF v0.2 (conventions in AGENT.md at the vault root).
#
#   sh okf_vault.sh check                   everything below; exit 1 if anything is off
#   sh okf_vault.sh stale                   which summaries need a rebuild, and why
#   sh okf_vault.sh stamp --by ACTOR FILE   after rebuilding a summary: sources, git hashes, generated
#   sh okf_vault.sh index                   regenerate every index.md (map and related blocks are kept)
#   sh okf_vault.sh frontmatter             give new notes their minimal OKF block
#   sh okf_vault.sh links [FILE...]         [[wikilinks]] -> relative markdown links; summaries stay current
#   sh okf_vault.sh hot [--days D] [--min N] [--recheck R]
#                                           often-changed files, the files citing them, and which are due a drift check
#   sh okf_vault.sh drift-stamp --by ACTOR FILE [SUMMARY...]
#                                           after a drift check of FILE: record it in the summaries checked
#
# The Python sits in the heredoc so the file stays inside the repos' .sh allow list.
exec python3 - "$0" "$@" <<'PY'
"""okf_vault: keep this Obsidian vault conformant with OKF v0.2.

Spec: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
Vault conventions (concept types, summary provenance with git blob hashes): AGENT.md.

Commands
  check                      Everything below; exit status 1 if anything is off.
  stale                      List stale summaries and why (changed/new/removed sources).
  stamp --by ACTOR FILE...   After rebuilding a summary: recompute its sources (with git blob
                             hashes), children and parent, and set generated.by/at to now.
  index                      Regenerate every index.md from the notes and summaries. Blocks
                             between <!-- map:start --> and <!-- map:end --> (the vault map in
                             the root index.md) and between <!-- related:start --> and
                             <!-- related:end --> (links that a folder's notes ask agents for)
                             are agent-maintained and kept as they are.
  frontmatter [--by ACTOR]   Give notes without an OKF type a minimal block
                             (type: Note, generated.by: ACTOR, default human:patrickCNMartin).
  links [FILE...]            Rewrite [[wikilinks]] (and links Obsidian shortened to a bare file
                             name) as relative markdown links, in every note or just FILE...;
                             then move each summary's recorded hashes (sources and drift_verification)
                             to the edited file's new hash, where the record was current, so a
                             link-only edit doesn't read as stale or as a change since a drift check;
                             drop drift_verification entries whose file was deleted or moved.
  hot [--days D] [--min N] [--recheck R]
                             Files that summaries are built from (and the task board) with at least
                             N changes in the last D days (default 30 days, 3 changes): commits in
                             the owning repo, plus one for uncommitted edits. For each, the summary
                             that hashes it and every agent-written file that links to it (related
                             blocks included), which is the list the scan command checks for drift.
                             Each summary's drift_verification says when it was last checked against
                             the file; it is due when never checked, or when changes to the file plus
                             edits to the summary's description or body since then reach R (default
                             3). A hot file is due when any of its summaries is, or when no summary
                             hashes or cites it.
  drift-stamp --by ACTOR FILE [SUMMARY...]
                             After a drift check of FILE: set its drift_verification entry (blob hash,
                             last commit, the summary's own content hash, time, actor) in each
                             SUMMARY, by default every summary that `hot` shows as due for FILE
                             (takes --recheck too).

Options
  --vault DIR                Vault root. Default: the nearest ancestor of this script, or of
                             the working directory, that contains .obsidian/.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import quote, unquote

HUMAN = 'human:patrickCNMartin'
HASH_METHOD = 'git hash-object'
OKF_VERSION = '0.2'
RESERVED = ('index.md', 'log.md')
SUMMARY_TYPE = 'Folder Summary'
BOARD_TYPE = 'Kanban Board'
# Concepts an agent drafts from a published paper, in a paper bundle (e.g. LabWiki/deqms-okf-bundle/)
PAPER_TYPES = ('Paper', 'Method', 'Algorithm', 'Finding', 'Dataset', 'Software', 'Reference')
AGENT_TYPES = (SUMMARY_TYPE, 'Agent Guide', 'Session Summary', 'Daily Recap') + PAPER_TYPES
# Agent-maintained blocks of an index.md, which `index` keeps as they are: the vault map (root only)
# and a folder's related links (the links its notes ask agents for, kept out of the notes).
KEEP_RE = re.compile(r'^<!-- (map|related):start -->[ \t]*$.*?^<!-- \1:end -->[ \t]*$', re.M | re.S)
RELATED_RE = re.compile(r'^<!-- related:start -->[ \t]*$.*?^<!-- related:end -->[ \t]*$', re.M | re.S)
# Files a summary is built from (hashed into `sources`); everything else is an attachment.
TEXT_EXT = {'.md', '.canvas', '.sh', '.nix', '.lock', '.txt', '.py', '.json', '.yaml', '.yml', '.toml'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.tif', '.tiff', '.bmp'}
# Frontmatter key order for summaries; unknown keys keep their place after these.
CANON = ['type', 'title', 'description', 'resource', 'tags', 'status', 'stale_after',
         'generated', 'verified', 'drift_verification', 'parent', 'children', 'hash_method', 'sources']
# A summary's record of when scan last checked it for drift against each file it hashes or cites.
DRIFT_KEY = 'drift_verification'
RECHECK = 3


# ---------------------------------------------------------------- files

def read(vault, rel):
    with open(os.path.join(vault, rel), encoding='utf-8', newline='') as f:
        return f.read()


def write(vault, rel, text):
    with open(os.path.join(vault, rel), 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def join(*parts):
    return os.path.join(*[p for p in parts if p])


def listdir(vault, d):
    """Visible subfolders and files of d, sorted."""
    try:
        entries = sorted(os.listdir(os.path.join(vault, d)), key=str.lower)
    except FileNotFoundError:
        return [], []
    dirs, files = [], []
    for e in entries:
        if e.startswith('.'):
            continue
        (dirs if os.path.isdir(os.path.join(vault, d, e)) else files).append(e)
    return dirs, files


def walk(vault, d=''):
    """Yield (dir, subdirs, files) for every visible folder under d."""
    dirs, files = listdir(vault, d)
    yield d, dirs, files
    for e in dirs:
        yield from walk(vault, join(d, e))


def md_files(vault):
    return [join(d, f) for d, _, files in walk(vault) for f in files if f.endswith('.md')]


def text_files(vault):
    return [join(d, f) for d, _, files in walk(vault) for f in files
            if os.path.splitext(f)[1].lower() in TEXT_EXT]


def is_repo_root(vault, d):
    return d == '' or os.path.exists(os.path.join(vault, d, '.git'))


def has_notes(vault, d):
    return any(f.endswith('.md') and f not in RESERVED for _, _, files in walk(vault, d) for f in files)


def git_hashes(vault, rels):
    """git hash-object for many vault-relative files at once."""
    if not rels:
        return {}
    out = subprocess.run(['git', 'hash-object', '--stdin-paths'], cwd=vault, check=True,
                         input='\n'.join(rels) + '\n', capture_output=True, text=True).stdout.split()
    return dict(zip(rels, out))


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------- frontmatter

FM_RE = re.compile(r'\A---[ \t]*\r?\n(?:(.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)', re.S)


def split_fm(text):
    """(frontmatter text or None, body)."""
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1) or '', text[m.end():]


def fm_blocks(fm):
    """Top-level keys of a frontmatter block, each with its raw lines, in order."""
    blocks = []
    for line in fm.split('\n'):
        m = re.match(r'([A-Za-z_][\w-]*)\s*:', line)
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
    m = re.search(r'^%s\s*:[ \t]*(.*?)[ \t]*$' % re.escape(key), fm or '', re.M)
    return unquote_yaml(m.group(1)) if m and m.group(1) else None


def fm_list(fm, key):
    """A top-level list of scalars (block or flow style)."""
    for k, lines in fm_blocks(fm or ''):
        if k != key:
            continue
        head = lines[0].split(':', 1)[1].strip()
        if head.startswith('['):
            return [unquote_yaml(x) for x in head.strip('[]').split(',') if x.strip()]
        return [unquote_yaml(l.strip()[2:]) for l in lines[1:] if l.strip().startswith('- ')]
    return []


SCALAR = r'("(?:[^"\\]|\\.)*"|\'(?:[^\']|\'\')*\'|[^,}]+?)'
SRC_FLOW = re.compile(r'^\s*-\s*\{\s*resource:\s*%s\s*,\s*hash:\s*([0-9a-f]{40})\s*\}\s*$' % SCALAR)


def fm_sources(fm):
    """[(resource, hash)] from a summary's `sources` block (flow or block entries)."""
    out, cur = [], None
    for k, lines in fm_blocks(fm or ''):
        if k != 'sources':
            continue
        for line in lines[1:]:
            m = SRC_FLOW.match(line)
            if m:
                out.append((unquote_yaml(m.group(1)), m.group(2)))
                continue
            m = re.match(r'^\s*(-\s+)?(resource|hash)\s*:\s*(.+?)\s*$', line)
            if not m:
                continue
            if m.group(1):
                cur = {}
                out.append(cur)
            if cur is not None:
                cur[m.group(2)] = unquote_yaml(m.group(3))
    return [x if isinstance(x, tuple) else (x.get('resource'), x.get('hash')) for x in out]


FLOW_ITEM = re.compile(r'^\s*-\s*\{(.*)\}\s*$')
PAIR_RE = re.compile(r'(\w+)\s*:\s*%s\s*(?:,|$)' % SCALAR)


def fm_drift(fm):
    """[{resource, hash, commit, at, by}] from a summary's drift_verification block."""
    for k, lines in fm_blocks(fm or ''):
        if k == DRIFT_KEY:
            items = (FLOW_ITEM.match(l) for l in lines[1:])
            return [{p.group(1): unquote_yaml(p.group(2)) for p in PAIR_RE.finditer(m.group(1).strip())}
                    for m in items if m]
    return []


def drift_lines(entries):
    """The drift_verification block: one flow mapping per file checked."""
    return ['%s:' % DRIFT_KEY] + [
        '  - { resource: %s, hash: %s, commit: %s, summary_hash: %s, at: %s, by: %s }'
        % (ys(e['resource']), e['hash'], e.get('commit') or 'none', e.get('summary_hash') or 'none',
           e['at'], ys(e['by'])) for e in entries]


def content_hash(text):
    """What a summary says: a git-style hash of its description and body. Frontmatter bookkeeping
    (generated, sources, drift_verification) is left out, so only real edits change it."""
    fm, body = split_fm(text)
    data = ((fm_get(fm, 'description') or '') + '\n' + body).encode('utf-8')
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def set_fm_block(text, key, lines, after=('verified', 'generated')):
    """Replace a top-level frontmatter key, or insert it after the first `after` key present."""
    fm, body = split_fm(text)
    blocks = fm_blocks(fm or '')
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
    if (PLAIN.fullmatch(s) and not s.endswith((' ', ':')) and ': ' not in s
            and s.lower() not in ('true', 'false', 'yes', 'no', 'on', 'off', 'null', '~')
            and not re.fullmatch(r'[\d.eE+:-]+', s)):
        return s
    return json.dumps(s, ensure_ascii=False)


def with_fm(fm_lines, body, nl='\n'):
    return '---' + nl + nl.join(fm_lines) + nl + '---' + nl + body


def h1(body):
    m = re.search(r'^# (.+?)\s*$', body, re.M)
    return m.group(1) if m else None


# ---------------------------------------------------------------- summaries

def summary_in(vault, d):
    _, files = listdir(vault, d)
    found = [f for f in files if f.endswith('_summary.md')]
    if not found:
        return None
    own = os.path.basename(d) + '_summary.md'
    return join(d, own if own in found else found[0])


def summaries(vault):
    return [s for s in (summary_in(vault, d) for d, _, _ in walk(vault)) if s]


def expected(vault, sdir):
    """(sources, children) a summary of folder sdir should record.

    sources: every text file in the folder, plus files in subfolders that have no summary
    of their own; children: the summaries of subfolders that do. Paths are relative to sdir.
    """
    sources, children = [], []

    def visit(d, prefix):
        dirs, files = listdir(vault, d)
        for f in files:
            if (os.path.splitext(f)[1].lower() in TEXT_EXT and f not in RESERVED
                    and not f.endswith('_summary.md')):
                sources.append(join(prefix, f))
        for e in dirs:
            p = join(d, e)
            if is_repo_root(vault, p):
                continue
            s = summary_in(vault, p)
            if s:
                children.append(join(prefix, e, os.path.basename(s)))
            else:
                visit(p, join(prefix, e))

    visit(sdir, '')
    return sorted(sources), sorted(children)


def parent_summary(vault, sdir):
    d = sdir
    while not is_repo_root(vault, d):
        d = os.path.dirname(d)
        s = summary_in(vault, d)
        if s:
            return s
    return None


def staleness(vault, spath):
    """List of (kind, detail) problems; empty when the summary is current."""
    fm, _ = split_fm(read(vault, spath))
    sdir = os.path.dirname(spath)
    recorded = dict(fm_sources(fm))
    srcs, kids = expected(vault, sdir)
    hashes = git_hashes(vault, [join(sdir, s) for s in srcs])
    problems = []
    for s in srcs:
        if s not in recorded:
            problems.append(('new', s))
        elif hashes[join(sdir, s)] != recorded[s]:
            problems.append(('changed', s))
    problems += [('removed', s) for s in recorded if s not in srcs]
    if sorted(fm_list(fm, 'children')) != kids:
        problems.append(('children', ', '.join(kids) or 'none'))
    return problems


def stamp(vault, spath, by, at=None):
    """Rewrite a summary's provenance block from the files on disk."""
    text = read(vault, spath)
    fm, body = split_fm(text)
    sdir = os.path.dirname(spath)
    srcs, kids = expected(vault, sdir)
    hashes = git_hashes(vault, [join(sdir, s) for s in srcs])
    parent = parent_summary(vault, sdir)
    managed = {
        'generated': ['generated: { by: %s, at: %s }' % (ys(by), at or now())],
        'parent': ['parent: ' + ys(os.path.relpath(parent, sdir or '.'))] if parent else None,
        'children': ['children:'] + ['  - ' + ys(c) for c in kids] if kids else None,
        'hash_method': ['hash_method: ' + HASH_METHOD],
        'sources': source_lines([(s, hashes[join(sdir, s)]) for s in srcs]),
    }
    write(vault, spath, with_fm(assemble(fm, managed, body), body))


def source_lines(pairs):
    """The `sources` block: one flow mapping per file, with its git blob hash."""
    return ['sources:'] + ['  - { resource: %s, hash: %s }' % (ys(r), h) for r, h in pairs] if pairs \
        else ['sources: []']


def assemble(fm, managed, body):
    """Frontmatter lines in canonical order: managed keys replaced, other keys kept."""
    blocks = [b for b in fm_blocks(fm or '') if b[0]]
    have = {k: lines for k, lines in blocks}
    have.setdefault('type', ['type: ' + SUMMARY_TYPE])
    if 'title' not in have and h1(body):
        have['title'] = ['title: ' + ys(h1(body))]
    for k, lines in managed.items():
        if lines:
            have[k] = lines
        else:
            have.pop(k, None)
    for k in ('built', 'folder'):  # pre-OKF keys: superseded by generated.at and the file's path
        have.pop(k, None)
    out = []
    for k in CANON:
        if k in have:
            out += [l for l in have[k] if l.strip()]
    for k, lines in blocks:
        if k not in CANON and k in have:
            out += [l for l in lines if l.strip()]
    return [l.rstrip() for l in out]


# ---------------------------------------------------------------- links

CODE_RE = re.compile(r'(```.*?```|`[^`\n]*`)', re.S)
WIKI_RE = re.compile(r'(!?)\[\[([^\]\n]+?)\]\]')
MDLINK_RE = re.compile(r'(!?)\[((?:[^\]\n]|\\\])*)\]\(([^)\s]+)\)')


def outside_code(text, fn):
    parts = CODE_RE.split(text)
    return ''.join(p if i % 2 else fn(p) for i, p in enumerate(parts))


def name_index(vault):
    """Obsidian-style link names -> vault-relative paths."""
    idx = {}
    for d, _, files in walk(vault):
        for f in files:
            p = join(d, f)
            idx.setdefault(f, []).append(p)
            if f.endswith('.md'):
                idx.setdefault(f[:-3], []).append(p)
    return idx


def resolve(idx, name, from_dir):
    """Resolve an Obsidian link target the way Obsidian does (closest match wins)."""
    name = name.strip()
    cands = idx.get(os.path.basename(name), [])
    if '/' in name:
        cands = [c for c in cands if c.endswith(name) or c.endswith(name + '.md')]
    if not cands:
        return None
    return sorted(cands, key=lambda c: (os.path.dirname(c) != from_dir,
                                        not c.startswith(from_dir), len(c)))[0]


def href(target, from_dir, heading=None):
    url = quote(os.path.relpath(target, from_dir or '.'), safe='/')
    return url + ('#' + quote(heading, safe=":,'") if heading else '')


def convert_links(vault, rel, text, idx=None):
    """Wikilinks and unresolvable relative links -> relative markdown links.

    Returns (new_text, unresolved_names).
    """
    idx = idx or name_index(vault)
    here = os.path.dirname(rel)
    missing = []

    def wiki(m):
        bang, inner = m.groups()
        target, _, alias = inner.partition('|')
        name, _, heading = target.partition('#')
        if not name:
            return '%s[%s](#%s)' % (bang, alias or heading, quote(heading, safe=":,'"))
        path = resolve(idx, name, here)
        if not path:
            missing.append(name)
            return m.group(0)
        if bang:  # an embed's alias is its display size: ![name|300](path)
            text_ = name + ('|' + alias if alias else '')
        else:
            text_ = alias or (name + (' § ' + heading if heading else ''))
        return '%s[%s](%s)' % (bang, text_, href(path, here, heading or None))

    def md(m):
        bang, label, url = m.groups()
        if re.match(r'[a-z][a-z0-9+.-]*:', url, re.I) or url.startswith('#'):
            return m.group(0)
        path, _, anchor = url.partition('#')
        if os.path.exists(os.path.join(vault, here, unquote(path))):
            return m.group(0)
        found = resolve(idx, unquote(path).lstrip('/'), here)
        if not found:
            missing.append(unquote(path))
            return m.group(0)
        return '%s[%s](%s)' % (bang, label, href(found, here) + ('#' + anchor if anchor else ''))

    return outside_code(text, lambda s: MDLINK_RE.sub(md, WIKI_RE.sub(wiki, s))), missing


def carry_hashes(vault, before, before_content=None):
    """After a link-only edit, move each summary's recorded hash to its source's new hash.

    Only where the record matched the file before the edit, so real staleness survives.
    before_content (summary -> content_hash before the edit) does the same for the summary_hash
    of its drift_verification entries, so a link fixed in the summary itself isn't an edit.
    Returns the summaries that changed.
    """
    after = git_hashes(vault, text_files(vault))
    updated = []

    def carried(f, h):
        return after[f] if before.get(f) == h and after.get(f, h) != h else h

    for s in summaries(vault):
        text = read(vault, s)
        fm, body = split_fm(text)
        sdir = os.path.dirname(s)
        old_c, new_c = (before_content or {}).get(s), content_hash(text)
        pairs = [(r, carried(join(sdir, r), h)) for r, h in fm_sources(fm)]
        drift = []
        for e in fm_drift(fm):
            f = os.path.normpath(join(sdir, e.get('resource', '')))
            if not os.path.exists(os.path.join(vault, f)):
                continue  # the file was deleted or moved: drop its entry (scan checks a new path afresh)
            e2 = dict(e, hash=carried(f, e.get('hash')))
            if old_c and e.get('summary_hash') == old_c:
                e2['summary_hash'] = new_c
            drift.append(e2)
        managed = {}
        if pairs != fm_sources(fm):
            managed['sources'] = source_lines(pairs)
        if drift != fm_drift(fm):  # a drift check of the old version still holds after a link-only edit
            managed[DRIFT_KEY] = drift_lines(drift)
        if managed:
            write(vault, s, with_fm(assemble(fm, managed, body), body))
            updated.append(s)
    return updated


def link_problems(vault, rel, broken=True):
    """Wikilinks, and (with broken=True) broken relative markdown links, in a file."""
    text = read(vault, rel)
    here = os.path.dirname(rel)
    found = []

    def scan(s):
        for m in WIKI_RE.finditer(s):
            found.append('wikilink ' + m.group(0))
        for m in MDLINK_RE.finditer(s if broken else ''):
            url = m.group(3)
            if re.match(r'[a-z][a-z0-9+.-]*:', url, re.I) or url.startswith('#'):
                continue
            if not os.path.exists(os.path.join(vault, here, unquote(url.partition('#')[0]))):
                found.append('broken ' + url)
        return s

    outside_code(text, scan)
    return found


# ---------------------------------------------------------------- index.md

def contents_descriptions(vault):
    """vault path -> one-line description, from every summary's Contents section."""
    out = {}
    for spath in summaries(vault):
        _, body = split_fm(read(vault, spath))
        m = re.search(r'^## Contents[ \t]*\n(.*?)(?=^#{1,2} |\Z)', body, re.M | re.S)
        if not m:
            continue
        sdir = os.path.dirname(spath)
        for line in m.group(1).splitlines():
            lm = re.match(r'\s*[-*]\s+(.+?)\s+—\s+(.+?)\s*$', line)
            if not lm:
                continue
            head, desc = lm.groups()
            if re.sub(r'\[[^\]]*\]\([^)]*\)|\([^)]*\)|`[^`]*`|[,\s]|and', '', head):
                continue  # not a plain list of files, e.g. "Child summaries: ..."
            desc = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', desc)
            for t in re.finditer(r'\]\(([^)#\s]+)[^)]*\)|`([^`]+)`', head):
                p = os.path.normpath(join(sdir, unquote(t.group(1) or t.group(2))))
                if os.path.basename(p) == 'index.md':  # a subfolder, linked through its index
                    p = os.path.dirname(p)
                if os.path.exists(os.path.join(vault, p)):
                    out.setdefault(p, desc)
    return out


def meta(vault, rel):
    """(title, description) of a note from its frontmatter."""
    fm, body = split_fm(read(vault, rel))
    return fm_get(fm, 'title'), fm_get(fm, 'description')


def entry(title, url, desc=None):
    return '* [%s](%s)%s' % (title, url, ' - ' + desc if desc else '')


def render_index(vault, d, descs, keep=None):
    """The index.md of folder d; keep is its agent-maintained blocks, appended as they are."""
    dirs, files = listdir(vault, d)
    out = []
    if is_repo_root(vault, d):
        out += ['---', 'okf_version: "%s"' % OKF_VERSION, '---', '']

    s = summary_in(vault, d)
    cover = s or parent_summary(vault, d)
    if cover:
        title, desc = meta(vault, cover)
        if not s:
            desc = 'Covers this folder. ' + (desc or '')
        out += ['# Summary', '', entry(title or os.path.basename(cover)[:-3],
                                      href(cover, d), desc), '']

    notes = [join(d, f) for f in files if f.endswith('.md') and f not in RESERVED and join(d, f) != s]
    if notes:
        out += ['# Notes', '']
        for n in notes:
            title, desc = meta(vault, n)
            out.append(entry(title or os.path.basename(n)[:-3], href(n, d), desc or descs.get(n)))
        out.append('')

    subs = [join(d, e) for e in dirs if has_notes(vault, join(d, e))]
    if subs:
        out += ['# Subfolders', '']
        for p in subs:
            cs = summary_in(vault, p)
            out.append(entry(os.path.basename(p), href(join(p, 'index.md'), d),
                             meta(vault, cs)[1] if cs else descs.get(p)))
        out.append('')

    others = [join(d, f) for f in files if not f.endswith('.md')]
    for e in dirs:
        if not has_notes(vault, join(d, e)):
            others += [join(sd, f) for sd, _, fs in walk(vault, join(d, e)) for f in fs]
    others = [o for o in others if os.path.splitext(o)[1].lower() not in IMAGE_EXT]
    if others:
        out += ['# Other files', '']
        out += [entry(os.path.relpath(o, d or '.'), href(o, d), descs.get(o)) for o in others]
        out.append('')

    text = '\n'.join(out).rstrip('\n') + '\n'
    return text + '\n' + keep + '\n' if keep else text


def index_targets(vault):
    return [d for d, _, _ in walk(vault) if has_notes(vault, d)]


def build_indexes(vault, dry=False):
    """Write (or with dry=True, list) every index.md that differs from its rendering."""
    descs = contents_descriptions(vault)
    changed = []
    for d in index_targets(vault):
        rel = join(d, 'index.md')
        old = read(vault, rel) if os.path.exists(os.path.join(vault, rel)) else None
        keep = '\n\n'.join(m.group(0) for m in KEEP_RE.finditer(old or ''))
        new = render_index(vault, d, descs, keep or None)
        if new != old:
            changed.append(rel)
            if not dry:
                write(vault, rel, new)
    return changed


# ---------------------------------------------------------------- raw notes

def add_frontmatter(vault, rel, by=HUMAN):
    """Give a note a minimal OKF block without touching its body. True if changed."""
    text = read(vault, rel)
    nl = '\r\n' if '\r\n' in text else '\n'
    fm, body = split_fm(text)
    if fm is None:
        write(vault, rel, with_fm(['type: Note', 'generated: { by: %s }' % ys(by)], text, nl))
        return True
    if fm_get(fm, 'type'):
        return False
    kind = 'Kanban Board' if re.search(r'^kanban-plugin\s*:', fm, re.M) else 'Note'
    add = ['type: ' + kind]
    if not re.search(r'^generated\s*:', fm, re.M):
        add.append('generated: { by: %s }' % ys(by))
    head = re.match(r'---[ \t]*\r?\n', text).end()
    write(vault, rel, text[:head] + nl.join(add) + nl + text[head:])
    return True


def note_type(vault, rel):
    fm, _ = split_fm(read(vault, rel))
    return fm_get(fm, 'type') if fm is not None else None


def agent_files(vault):
    return [p for p in md_files(vault)
            if os.path.basename(p) not in RESERVED and note_type(vault, p) in AGENT_TYPES]


def boards(vault):
    return [p for p in md_files(vault)
            if os.path.basename(p) not in RESERVED and note_type(vault, p) == BOARD_TYPE]


# ---------------------------------------------------------------- hot files

def repos(vault):
    """The git repos in the vault, as vault-relative folders ('' is the root)."""
    return [d for d, _, _ in walk(vault) if os.path.exists(os.path.join(vault, d, '.git'))]


def git_paths(vault, repo, *args):
    """NUL-separated paths from a git command run with -z, as vault-relative paths."""
    out = subprocess.run(['git', *args], cwd=os.path.join(vault, repo),
                         capture_output=True, text=True).stdout
    return [t.strip('\n') for t in out.split('\0') if t.strip('\n')]


def changes(vault, days):
    """vault path -> (commits touching it in the last `days` days, True if it has uncommitted edits)."""
    commits, dirty = {}, set()
    for repo in repos(vault):
        for p in git_paths(vault, repo, 'log', '-z', '--since=%d.days' % days, '--name-only', '--format='):
            commits[join(repo, p)] = commits.get(join(repo, p), 0) + 1
        entries = git_paths(vault, repo, 'status', '--porcelain', '-z', '-uall')
        skip = False
        for e in entries:
            if skip:  # the original path of a rename or copy
                skip = False
                continue
            dirty.add(join(repo, e[3:]))
            skip = e[0] in 'RC'
    return {p: (commits.get(p, 0), p in dirty) for p in set(commits) | dirty}


def citations(vault):
    """vault path -> {agent-written file: number of links to it}. The recap has its own fingerprints.
    A folder's index.md counts only through its related block; the root one counts whole (the map)."""
    refs = {}
    citers = {p: read(vault, p) for p in agent_files(vault) if note_type(vault, p) != 'Daily Recap'}
    citers['index.md'] = read(vault, 'index.md')
    for d in index_targets(vault):
        rel = join(d, 'index.md')
        if d and os.path.exists(os.path.join(vault, rel)):
            block = '\n'.join(m.group(0) for m in RELATED_RE.finditer(read(vault, rel)))
            if block:
                citers[rel] = block
    for f, text in citers.items():
        here = os.path.dirname(f)

        def scan(s):
            for m in MDLINK_RE.finditer(s):
                url = m.group(3)
                if re.match(r'[a-z][a-z0-9+.-]*:', url, re.I) or url.startswith('#'):
                    continue
                p = os.path.normpath(join(here, unquote(url.partition('#')[0])))
                refs.setdefault(p, {})[f] = refs.get(p, {}).get(f, 0) + 1
            return s

        outside_code(text, scan)
    return refs


def covers(vault):
    """vault path -> the summary that hashes it."""
    cover = {}
    for s in summaries(vault):
        sdir = os.path.dirname(s)
        for src in expected(vault, sdir)[0]:
            cover[join(sdir, src)] = s
    return cover


def iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def owning_repo(vault, rel):
    d = os.path.dirname(rel)
    while not is_repo_root(vault, d):
        d = os.path.dirname(d)
    return d


_history = {}


def history(vault, rel):
    """[(commit, date, blob)] for the commits that changed rel, newest first (blob None once deleted)."""
    if rel not in _history:
        repo = owning_repo(vault, rel)
        out = subprocess.run(['git', 'log', '--format=%x01%H %cI', '--raw', '--no-abbrev', '--',
                              os.path.relpath(rel, repo or '.')], cwd=os.path.join(vault, repo),
                             capture_output=True, text=True).stdout
        rows = []
        for chunk in out.split('\x01')[1:]:
            lines = chunk.strip('\n').split('\n')
            commit, date = lines[0].split()
            raw = [l.split()[3] for l in lines[1:] if l.startswith(':')]
            blob = raw[0] if raw and raw[0].strip('0') else None
            rows.append((commit[:7], iso(date), blob))
        _history[rel] = rows
    return _history[rel]


def changes_since(vault, rel, entry):
    """How many times rel has changed since the version a drift_verification entry records:
    commits that changed it after that version, plus one for uncommitted edits."""
    cur = git_hashes(vault, [rel])[rel]
    if cur == entry.get('hash'):
        return 0
    hist = history(vault, rel)
    dirty = 1 if not hist or hist[0][2] != cur else 0
    for i, (_, _, blob) in enumerate(hist):
        if blob == entry.get('hash'):
            return dirty + i
    # The checked version was never committed (it was edited again first): count the later commits.
    try:
        at = iso(entry.get('at') or '')
    except ValueError:
        return dirty + len(hist)
    return dirty + sum(1 for _, date, _ in hist if date > at)


def blob_text(vault, rel, blob):
    out = subprocess.run(['git', 'cat-file', '-p', blob], cwd=os.path.join(vault, owning_repo(vault, rel)),
                         capture_output=True).stdout
    return out.decode('utf-8', 'replace')


def edits_since(vault, s, entry):
    """How many times summary s has been edited since the check a drift_verification entry records:
    changes to its description or body (not frontmatter bookkeeping), committed or not."""
    want = entry.get('summary_hash')
    prev = content_hash(read(vault, s))
    if prev == want:
        return 0
    try:
        at = iso(entry.get('at') or '')
    except ValueError:
        at = None
    n = 0
    for _, date, blob in history(vault, s):
        if blob is None:
            break
        h = content_hash(blob_text(vault, s, blob))
        if h != prev:
            n, prev = n + 1, h
        if h == want:
            return n
        if at and date <= at:  # the checked text was never committed (edited again first)
            break
    return max(n, 1)


def drift_checks(vault, p, s, refs, recheck):
    """{file: (kind, entry, (changes to p, edits to the summary) since, due)} for the summary
    hashing p (s) and the files citing it.

    kind 'tag': a summary, whose drift_verification entry for p says when it was last checked; due
    when there is none, or when changes to p plus edits to the summary since then reach `recheck`.
    'record': a session summary, never checked. 'untagged': index.md (the map, related blocks) or
    AGENT.md, checked whenever p is due.
    """
    out = {}
    for f in ([s] if s else []) + sorted(f for f in refs if f != s):
        kind = {SUMMARY_TYPE: 'tag', 'Session Summary': 'record'}.get(note_type(vault, f), 'untagged')
        if kind != 'tag':
            out[f] = (kind, None, None, None)
            continue
        here = os.path.dirname(f)
        entry = next((e for e in fm_drift(split_fm(read(vault, f))[0])
                      if os.path.normpath(join(here, e.get('resource', ''))) == p), None)
        n = (changes_since(vault, p, entry), edits_since(vault, f, entry)) if entry else None
        out[f] = (kind, entry, n, n is None or sum(n) >= recheck)
    return out


def is_due(checks):
    """A hot file is due when one of its summaries is, or when no summary hashes or cites it."""
    tagged = [c for c in checks.values() if c[0] == 'tag']
    return not tagged or any(c[3] for c in tagged)


def hot(vault, days, least, recheck=RECHECK):
    """[(path, commits, dirty, covering summary or None, summary status, {citer: links}, drift checks)],
    hottest first."""
    cover = covers(vault)
    watched = set(cover) | set(boards(vault))
    counts = changes(vault, days)
    refs = citations(vault)
    rows = []
    for p in watched:
        n, dirty = counts.get(p, (0, False))
        if n + dirty < least:
            continue
        s, status = cover.get(p), None
        if s:
            recorded = dict(fm_sources(split_fm(read(vault, s))[0]))
            r = os.path.relpath(p, os.path.dirname(s) or '.')
            status = ('stale: new' if r not in recorded else
                      'current' if git_hashes(vault, [p])[p] == recorded[r] else 'stale: changed')
        cited = {f: k for f, k in refs.get(p, {}).items() if f != s}
        rows.append((p, n, dirty, s, status, cited, drift_checks(vault, p, s, cited, recheck)))
    return sorted(rows, key=lambda r: (-(r[1] + r[2]), r[0]))


def drift_stamp(vault, p, by, files=None, recheck=RECHECK):
    """Record a drift check of p in the given summaries, or in every summary due for p.
    Returns (stamped, refused): files that are not summaries can't hold the tag."""
    if files is None:
        s = covers(vault).get(p)
        checks = drift_checks(vault, p, s, citations(vault).get(p, {}), recheck)
        files = [f for f, c in checks.items() if c[0] == 'tag' and c[3]]
    hist = history(vault, p)
    new = {'hash': git_hashes(vault, [p])[p], 'commit': hist[0][0] if hist else 'none', 'at': now(), 'by': by}
    stamped, refused = [], []
    for f in files:
        if note_type(vault, f) != SUMMARY_TYPE:
            refused.append(f)
            continue
        text = read(vault, f)
        here = os.path.dirname(f)
        entries = [e for e in fm_drift(split_fm(text)[0])
                   if os.path.normpath(join(here, e.get('resource', ''))) != p]
        entries.append(dict(new, resource=os.path.relpath(p, here or '.'), summary_hash=content_hash(text)))
        entries.sort(key=lambda e: e['resource'])
        write(vault, f, set_fm_block(text, DRIFT_KEY, drift_lines(entries)))
        stamped.append(f)
    return stamped, refused


# ---------------------------------------------------------------- check

def check(vault):
    problems = []
    for p in md_files(vault):
        base = os.path.basename(p)
        fm, body = split_fm(read(vault, p))
        if base == 'index.md':
            allowed = is_repo_root(vault, os.path.dirname(p))
            if fm is not None and not (allowed and set(k for k, _ in fm_blocks(fm) if k) <= {'okf_version'}):
                problems.append((p, 'index.md may only carry okf_version, and only at a bundle root'))
        elif base == 'log.md':
            bad = [h for h in re.findall(r'^## (.+)$', body, re.M) if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', h.strip())]
            if bad:
                problems.append((p, 'log.md date headings must be YYYY-MM-DD: ' + ', '.join(bad)))
        elif fm is None:
            problems.append((p, 'no frontmatter (run: frontmatter)'))
        elif not fm_get(fm, 'type'):
            problems.append((p, 'frontmatter has no type (run: frontmatter)'))
    for s in summaries(vault):
        for kind, detail in staleness(vault, s):
            problems.append((s, 'stale: %s %s' % (kind, detail)))
        here = os.path.dirname(s)
        for e in fm_drift(split_fm(read(vault, s))[0]):
            if not os.path.exists(os.path.join(vault, here, e.get('resource', ''))):
                problems.append((s, 'drift_verification names a missing file: %s (run: links)'
                                 % e.get('resource')))
    for rel in build_indexes(vault, dry=True):
        problems.append((rel, 'out of date (run: index)'))
    # Every note uses markdown links. Broken ones are only checked in agent-written files and the
    # task board (no summary hashes it): a raw note may link a note that isn't written yet (OKF allows it).
    agent = set(agent_files(vault) + boards(vault) + [join(d, 'index.md') for d in index_targets(vault)])
    for p in md_files(vault):
        if os.path.basename(p) != 'log.md' and (p in agent or os.path.basename(p) != 'index.md'):
            for msg in link_problems(vault, p, broken=p in agent):
                problems.append((p, msg + (' (run: links)' if msg.startswith('wikilink') else '')))
    return problems


# ---------------------------------------------------------------- cli

def find_vault(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, '.obsidian')):
            return d
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def rel_arg(vault, p):
    return os.path.relpath(os.path.abspath(p), vault)


def main(argv, script=None):
    args = list(argv)
    opt = {}
    for flag in ('--vault', '--by', '--days', '--min', '--recheck'):
        if flag in args:
            i = args.index(flag)
            opt[flag] = args[i + 1]
            del args[i:i + 2]
    vault = opt.get('--vault') or (script and find_vault(os.path.dirname(script))) or find_vault(os.getcwd())
    if not vault or not args:
        print(__doc__)
        return 2
    vault = os.path.abspath(vault)
    cmd, rest = args[0], args[1:]

    if cmd == 'check':
        problems = check(vault)
        for p, msg in problems:
            print('%s: %s' % (p, msg))
        print('OK: vault is OKF %s conformant and current.' % OKF_VERSION if not problems
              else '%d problem(s).' % len(problems))
        return 1 if problems else 0
    if cmd == 'stale':
        n = 0
        for s in summaries(vault):
            probs = staleness(vault, s)
            if probs:
                n += 1
                print(s)
                for kind, detail in probs:
                    print('    %-8s %s' % (kind, detail))
        print('%d stale summary(ies).' % n)
        return 1 if n else 0
    if cmd == 'stamp':
        if '--by' not in opt or not rest:
            print('usage: stamp --by ACTOR SUMMARY...   (e.g. --by claude-code/claude-opus-5-5)')
            return 2
        for p in rest:
            stamp(vault, rel_arg(vault, p), opt['--by'])
            print('stamped', rel_arg(vault, p))
        return 0
    if cmd == 'index':
        for rel in build_indexes(vault):
            print('wrote', rel)
        return 0
    if cmd == 'frontmatter':
        for p in md_files(vault):
            if (os.path.basename(p) not in RESERVED and not p.endswith('_summary.md')
                    and add_frontmatter(vault, p, opt.get('--by', HUMAN))):
                print('added frontmatter:', p)
        return 0
    if cmd == 'links':
        idx = name_index(vault)
        before = git_hashes(vault, text_files(vault))
        before_content = {s: content_hash(read(vault, s)) for s in summaries(vault)}
        targets = [rel_arg(vault, x) for x in rest] or [
            p for p in md_files(vault) if os.path.basename(p) not in RESERVED]
        for p in targets:
            text = read(vault, p)
            new, missing = convert_links(vault, p, text, idx)
            if new != text:
                write(vault, p, new)
                print('rewrote links:', p)
            for name in missing:
                print('  unresolved in %s: %s' % (p, name))
        for s in carry_hashes(vault, before, before_content):
            print('carried hashes forward:', s)
        return 0
    if cmd == 'hot':
        days, least = int(opt.get('--days', 30)), int(opt.get('--min', 3))
        recheck = int(opt.get('--recheck', RECHECK))
        rows = hot(vault, days, least, recheck)
        print('%d hot file(s): %d or more changes in the last %d days '
              '(commits, plus 1 for uncommitted edits).' % (len(rows), least, days))
        print('%d due for a drift check: a summary never checked against it, or %d or more changes to '
              'the file and edits to the summary since its check.' % (sum(is_due(r[6]) for r in rows), recheck))

        def drift(c):
            kind, e, k, due = c
            if kind == 'record':
                return 'session summary: never checked'
            if kind == 'untagged':
                return 'no tag: checked when the file is due'
            if not e:
                return 'never checked: DUE'
            return 'checked %s, %d change%s since%s%s' % (
                e.get('at', '?')[:10], k[0], '' if k[0] == 1 else 's',
                ' + %d summary edit%s' % (k[1], '' if k[1] == 1 else 's') if k[1] else '', ': DUE' if due else '')

        for p, n, dirty, s, status, refs, checks in rows:
            print('\n%3d  %s   (%d commit(s)%s)   %s' % (n + dirty, p, n, ' + uncommitted' if dirty else '',
                                                       'DUE' if is_due(checks) else 'skip: checked'))
            print('       summary   %s' % ('%s (%s; %s)' % (s, status, drift(checks[s])) if s
                                           else 'none: no summary hashes it'))
            for f, k in sorted(refs.items()):
                print('       cited by  %s (%d link%s; %s)' % (f, k, 's' if k > 1 else '', drift(checks[f])))
        return 0
    if cmd == 'drift-stamp':
        if '--by' not in opt or not rest:
            print('usage: drift-stamp --by ACTOR FILE [SUMMARY...]   (after a drift check of FILE)')
            return 2
        p = rel_arg(vault, rest[0])
        if not os.path.isfile(os.path.join(vault, p)):
            print('no such file:', p)
            return 2
        files = [rel_arg(vault, x) for x in rest[1:]] or None
        stamped, refused = drift_stamp(vault, p, opt['--by'], files, int(opt.get('--recheck', RECHECK)))
        for f in stamped:
            print('drift-stamped', f)
        for f in refused:
            print('  not a summary, no tag:', f)
        if not stamped and not refused:
            print('nothing due for', p)
        return 1 if refused else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[2:], sys.argv[1]))
PY
