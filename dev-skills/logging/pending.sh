#!/bin/sh
# Audit-log entries that do not name their commit: the hash is `uncommitted`, missing,
# or not a commit in this repo. Prints one line per entry; exit 0 none, 1 some, 2 cannot check.
# Reads entry headers only (`## YYYY-MM-DD — <hash> — <title>`), and only those below a
# `<!-- hashes from here -->` line when the log has one: entries above it predate hashes.
# Run from the repo root: sh dev-skills/logging/pending.sh [log]
log=${1:-logs/audit_log.md}
[ -f "$log" ] || { echo "pending.sh: no audit log at $log" >&2; exit 2; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "pending.sh: not in a git repo" >&2; exit 2; }

start=$(grep -n '^<!-- hashes from here -->' "$log" | tail -n 1 | cut -d: -f1)
found=0
tail -n +"$((${start:-0} + 1))" "$log" | grep -E '^## [0-9]{4}-[0-9]{2}-[0-9]{2} — ' > "${TMPDIR:-/tmp}/pending.$$"
while IFS= read -r header; do
    rest=${header#* — }
    hash=${rest%%[ ,]*}
    case $hash in
        uncommitted) why=uncommitted ;;
        *[!0-9a-f]* | '') why='no hash' ;;
        *) if [ ${#hash} -lt 7 ] || ! git cat-file -e "$hash^{commit}" 2>/dev/null; then
               why="no commit $hash here"
           else continue; fi ;;
    esac
    echo "$why: $header"
    found=1
done < "${TMPDIR:-/tmp}/pending.$$"
rm -f "${TMPDIR:-/tmp}/pending.$$"
exit $found
