#!/usr/bin/env bash
# Ship a Splatbox version in one go. Only run the real thing when Max says so.
#
#   ./ship.sh --check 048                                 dry run: checks everything, changes and pushes nothing
#   ./ship.sh 048 "short message" --tests full           real release, full test run (about 25 min: run it with nohup)
#   ./ship.sh 048 "short message" --tests "dock tl2"      only suites whose names contain those words
#   ./ship.sh 048 "short message" --tests area:timeline   suites for an area in tools/areas.txt
#   ./ship.sh 048 "short message" --tests skip            no tests. Says so in the commit message. Use rarely.
#
# What it does: checks CHANGELOG.md has "## Version 048" -> bumps VERSION in app/index.html and app/sw.js ->
# runs the tests (a failing suite is re-run alone once; passing alone is reported as a flake, not hidden) ->
# release.sh stable (copies app/ -> root: the step missed in V047) -> checks root == app -> commits -> pushes (3 tries) ->
# waits for the Pages deploy and the Windows build -> checks the live page shows the new version.
# SHIP_LOCAL=1 is for testing this script against a throwaway remote: skips the GitHub and live checks.
# Tags are not pushed: the sandbox can't (see RELEASING.md).
set -uo pipefail
cd "$(dirname "$0")"
REPO=Donsteezlesgit/splatbox
LIVE=https://donsteezlesgit.github.io/Splatbox/index.html
DRY=0; ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --check) DRY=1; shift;;
    --tests) TESTS="${2:-}"; shift 2;;
    *) ARGS+=("$1"); shift;;
  esac
done
N="${ARGS[0]:-}"; MSG="${ARGS[1]:-}"; TESTS="${TESTS:-}"
die(){ echo "STOP: $*" >&2; exit 1; }
ok(){ echo "  ok   $*"; }
note(){ echo "  note $*"; }
[ -n "$N" ] || die "usage: ./ship.sh [--check] 048 \"message\" --tests full|\"names\"|area:NAME|skip"
[[ "$N" =~ ^[0-9]{3}$ ]] || die "version must be three digits, like 048"
[ "$DRY" = 1 ] || [ -n "$MSG" ] || die "give a short message for the commit"
[ "$DRY" = 1 ] || [ -n "$TESTS" ] || die "say what to test: --tests full | \"dock tl2\" | area:timeline | skip"
rootver=$(grep -o 'var VERSION="Version [0-9]*"' index.html | grep -o '[0-9][0-9]*')
appver=$(grep -o 'var VERSION="Version [0-9]*"' app/index.html | grep -o '[0-9][0-9]*')
echo "== Checks (live root is $rootver, app/ is $appver, shipping $N)"
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || die "not on main"
[ $((10#$N)) -gt $((10#$rootver)) ] || die "version $N is not newer than the live $rootver"
ok "version $N is newer than the live $rootver"
grep -q "^## Version $N\b" CHANGELOG.md || die "CHANGELOG.md has no '## Version $N' section"
ok "changelog has a Version $N section"
grep -q "ship.sh" CLAUDE.md || note "CLAUDE.md does not mention ship.sh"
[ "${SHIP_LOCAL:-0}" = 1 ] || { gh run list --limit 1 >/dev/null 2>&1 && ok "gh can read the repo's runs" || die "gh can't read the repo's runs (needed to check the deploy)"; }
git ls-remote origin HEAD >/dev/null 2>&1 && ok "the remote is reachable" || die "can't reach the remote"
git diff --quiet HEAD -- index.html sw.js || die "root index.html/sw.js have hand edits: never edit the root, only app/"
ok "root files have no hand edits"

# which suites
SUITES=""; FULL=0
case "$TESTS" in
  "") ;;
  full) FULL=1;;
  skip) ;;
  area:*) a="${TESTS#area:}"; SUITES=$(grep -E "^$a[[:space:]]" tools/areas.txt | sed -E "s/^[^[:space:]]+[[:space:]]+//"); [ -n "$SUITES" ] || die "no area '$a' in tools/areas.txt";;
  *) SUITES="$TESTS";;
esac
if [ -n "$SUITES" ]; then
  for s in $SUITES; do grep -q "(\"$s\"" tests/run.py || die "no test suite named '$s' (see TESTS in tests/run.py)"; done
  ok "suites: $SUITES"
fi
[ "$FULL" = 1 ] && ok "tests: full run"
[ "$TESTS" = skip ] && note "tests will be SKIPPED and the commit will say so"
if [ "$DRY" = 1 ]; then
  cmp -s app/index.html index.html && note "root already equals app/" || note "root differs from app/ (normal before release)"
  echo "== Dry run finished. Nothing was changed or pushed."; exit 0
fi

echo "== Bump version"
sed -i "s/var VERSION=\"Version [0-9]*\"/var VERSION=\"Version $N\"/" app/index.html
sed -i "s/const VERSION='Version [0-9]*'/const VERSION='Version $N'/" app/sw.js
grep -q "Version $N" app/index.html && grep -q "Version $N" app/sw.js || die "version bump failed"
ok "app/index.html and app/sw.js are Version $N"

echo "== Tests"
TNOTE=""
run_tests(){ # $1 = suite name or empty for all; output to $2
  if [ -n "$1" ]; then python3 tests/run.py "$1" > "$2" 2>&1; else python3 tests/run.py > "$2" 2>&1; fi
}
if [ "$TESTS" = skip ]; then
  TNOTE="Tests: skipped."
else
  LOG=/tmp/ship-tests.log; : > "$LOG"; FAILED=""
  if [ "$FULL" = 1 ]; then
    run_tests "" /tmp/ship-t.log; cat /tmp/ship-t.log >> "$LOG"
    FAILED=$(awk '/^== /{s=$2} /^  FAIL /{print s}' /tmp/ship-t.log | sort -u)
    ran="full run"
  else
    for s in $SUITES; do run_tests "$s" /tmp/ship-t.log; cat /tmp/ship-t.log >> "$LOG"
      grep -q "^  FAIL " /tmp/ship-t.log && FAILED="$FAILED $s"; done
    ran="suites: $SUITES"
  fi
  [ -f tests/inbox_queue.js ] && { node tests/inbox_queue.js >> "$LOG" 2>&1 || FAILED="$FAILED inbox_queue.js"; }
  FLAKY=""; REAL=""
  for s in $FAILED; do
    if [ "$s" = inbox_queue.js ]; then REAL="$REAL $s"; continue; fi
    run_tests "$s" /tmp/ship-r.log
    if grep -q "^  FAIL " /tmp/ship-r.log; then REAL="$REAL $s"; else FLAKY="$FLAKY $s"; fi
  done
  P=$(grep -c "^  PASS " "$LOG"); F=$(grep -c "^  FAIL " "$LOG")
  echo "  $P passed, $F failed in the first pass ($ran)"
  [ -n "$FLAKY" ] && note "failed under load but passed when re-run alone:$FLAKY"
  if [ -n "$REAL" ]; then
    grep "^  FAIL " "$LOG" | head -20
    sed -i "s/var VERSION=\"Version [0-9]*\"/var VERSION=\"Version $appver\"/" app/index.html
    sed -i "s/const VERSION='Version [0-9]*'/const VERSION='Version $appver'/" app/sw.js
    die "real failures in:$REAL. Not releasing. Version bump undone. Log: $LOG"
  fi
  TNOTE="Tests: $ran, $P passed first pass"; [ -n "$FLAKY" ] && TNOTE="$TNOTE; flaky under load, passed alone:$FLAKY"; TNOTE="$TNOTE."
fi

echo "== Release copy"
SKIP_TESTS=1 ./release.sh stable | sed 's/^/  /' || die "release.sh failed"
cmp -s app/index.html index.html && cmp -s app/sw.js sw.js || die "root does not match app/ after release.sh"
ok "root index.html and sw.js now equal app/"

echo "== Commit"
git add -A
git commit -q -F - <<EOF || die "commit failed"
Version $N: $MSG

$TNOTE

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: ${CLAUDE_SESSION_URL:-https://claude.ai/code/session_01KMLZ697HhEBW9sb6QRCC7K}
EOF
SHA=$(git rev-parse HEAD); ok "committed ${SHA:0:7}"

echo "== Push"
PUSHED=0
for i in 1 2 3; do
  if git push origin HEAD:main >/tmp/ship-push.log 2>&1; then PUSHED=1; break; fi
  note "push attempt $i failed, retrying"; sleep 5
done
[ "$PUSHED" = 1 ] || { cat /tmp/ship-push.log; die "push failed 3 times. The commit is local ($SHA)."; }
ok "pushed to main"

[ "${SHIP_LOCAL:-0}" = 1 ] && { echo "== Local test mode: skipped the GitHub and live checks"; echo "== Done: Version $N"; exit 0; }
echo "== Waiting for GitHub (up to 10 min)"
REV=$(tr -d '[:space:]' < desktop/REV)
for i in $(seq 1 40); do
  J=$(gh run list --commit "$SHA" --json name,status,conclusion 2>/dev/null)
  pages=$(echo "$J" | python3 -c "import sys,json;r=[x for x in json.load(sys.stdin) if 'pages' in x['name']];print(r[0]['conclusion'] or r[0]['status'] if r else 'waiting')" 2>/dev/null || echo waiting)
  win=$(echo "$J" | python3 -c "import sys,json;r=[x for x in json.load(sys.stdin) if x['name']=='Windows app'];print(r[0]['conclusion'] or r[0]['status'] if r else 'waiting')" 2>/dev/null || echo waiting)
  [ "$pages" = success ] && [ "$win" = success ] && break
  { [ "$pages" = failure ] || [ "$win" = failure ]; } && break
  sleep 15
done
[ "$pages" = success ] && ok "Pages deploy: success" || echo "  FAIL Pages deploy: $pages"
[ "$win" = success ] && ok "Windows build: success" || echo "  FAIL Windows build: $win"
rel="0.$((10#$N)).$REV"
gh release list --limit 6 2>/dev/null | grep -q "$rel" && ok "Windows release v$rel is published" || note "Windows release v$rel not listed yet"

echo "== Live page"
LV=$(curl -s --max-time 20 "$LIVE?v=$SHA" 2>/dev/null | grep -o 'var VERSION="Version [0-9]*"' | grep -o '[0-9][0-9]*' | head -1)
if [ "$LV" = "$N" ]; then ok "the live page says Version $N"
elif [ -z "$LV" ]; then note "couldn't read the live page from here (sandbox network). Check it by hand: $LIVE"
else echo "  FAIL live page says Version $LV, expected $N (the CDN can lag a minute: check again)"; fi
note "no tag pushed (the sandbox can't; see RELEASING.md)"
echo "== Done: Version $N"
