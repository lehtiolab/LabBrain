#!/bin/sh
# The audit log, read from the decision records: one file per decision in $dir, holding no hash.
# Each record's hash is looked up in git every time this runs: the commit that added the file.
#   sh dev-skills/logging/log.sh                prints $old (frozen), then every record oldest
#                                               first, under `## YYYY-MM-DD — <hash> — <title>`
#   sh dev-skills/logging/log.sh --uncommitted  lists records not committed, or edited since;
#                                               exit 0 none, 1 some, 2 cannot check
# Needs the full history: in a shallow clone, older records show the wrong hash.
dir=logs/decisions
old=logs/audit_log.md

git rev-parse --git-dir >/dev/null 2>&1 || { echo "log.sh: not in a git repo" >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)" || exit 2

if [ "$1" = --uncommitted ]; then
    [ -d "$dir" ] || exit 0
    status=$(git -c core.quotePath=false status --porcelain --untracked-files=all -- "$dir") || exit 2
    [ -n "$status" ] || exit 0
    printf '%s\n' "$status" | awk '{
        x = substr($0, 1, 1); y = substr($0, 2, 1); what = "edited since its commit"
        if (x == "?" || x == "A") what = "not committed"
        else if (x == "D" || y == "D") what = "deleted"
        else if (x == "R") what = "renamed"
        print what ": " substr($0, 4) }'
    exit 1
fi
[ $# -eq 0 ] || { echo "usage: sh dev-skills/logging/log.sh [--uncommitted]" >&2; exit 2; }

[ ! -f "$old" ] || { cat "$old"; printf '\n<!-- end of %s; from here, one record per decision in %s/ -->\n' "$old" "$dir"; }
set -- "$dir"/*.md
[ -f "$1" ] || exit 0

# Which commit added each record, oldest first. --no-renames: a renamed record is added anew.
added=${TMPDIR:-/tmp}/log.$$
trap 'rm -f "$added"' EXIT
git -c core.quotePath=false log --reverse --no-renames --diff-filter=A --format=@%h --name-only \
    -- "$dir" > "$added" || exit 2

# Order: the date the name starts with, then the order the records were committed in.
tab=$(printf '\t')
order=$(printf '%s\n' "$@" | awk -v tab="$tab" '
    FILENAME == ARGV[1] { if (substr($0, 1, 1) == "@") n++; else if ($0 != "") at[$0] = n; next }
    { name = $0; sub(/.*\//, "", name)
      print substr(name, 1, 10) tab (($0 in at) ? at[$0] : 999999999) tab $0 }' "$added" - |
    sort -t "$tab" -k1,1 -k2,2n | cut -f3)

set -f
IFS='
'
# shellcheck disable=SC2086 # one record per line; names hold no spaces
awk '
    function header() {
        if (title == "") title = name
        if (date == "") date = substr(name, 1, 10)
        printf "\n---\n\n## %s — %s — %s\n\n", date, ((file in hash) ? hash[file] : "uncommitted"), title
        if (by != "") print "**Decided by:** " by
        if (sup != "") print "**Supersedes:** " sup
        if (by != "" || sup != "") print ""
        state = 2; lead = 1
    }
    FILENAME == ARGV[1] { if (substr($0, 1, 1) == "@") h = substr($0, 2); else if ($0 != "") hash[$0] = h; next }
    FNR == 1 {
        if (state == 1) header()
        file = FILENAME; name = file; sub(/.*\//, "", name); date = title = by = sup = ""
        if ($0 == "---") { state = 1; next }
        header()
    }
    state == 1 {
        if ($0 == "---") { header(); next }
        k = $0; sub(/:.*/, "", k); v = $0; sub(/^[^:]*:[ \t]*/, "", v); sub(/[ \t]+$/, "", v)
        if (v ~ /^".*"$/) v = substr(v, 2, length(v) - 2)
        if (k == "date") date = v
        else if (k == "title") title = v
        else if (k == "decided_by") { gsub(/^\[|\]$/, "", v); by = v }
        else if (k == "supersedes") sup = v
        next
    }
    state == 2 { if (lead && $0 ~ /^[ \t]*$/) next; lead = 0; print }
    END { if (state == 1) header() }' "$added" $order
