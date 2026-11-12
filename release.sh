#!/usr/bin/env bash
# Splatbox release helper. Source of truth is app/. Root = stable (what Max uses). beta/ = the test copy.
#   ./release.sh test              run the whole test suite
#   ./release.sh beta              tests, then copy app/ -> beta/
#   ./release.sh stable            tests, then copy app/ -> root   (small fixes)
#   ./release.sh promote           copy beta/ -> root, no re-test of new code (what you tested is what ships)
#   ./release.sh rollback v018     put root back to how an old tag had it
# After beta/stable/promote/rollback: git add -A, git commit, git tag, git push.  (tag name printed for you)
set -euo pipefail
cd "$(dirname "$0")"
ver(){ grep -o 'var VERSION="Version [0-9]*"' "$1" | grep -o '[0-9][0-9]*'; }
tests(){ if [ "${SKIP_TESTS:-0}" = 1 ]; then echo "(tests skipped)"; else python3 tests/run.py; fi; }
mkbeta_manifest(){
  python3 - <<'P'
import json
m=json.load(open('manifest.webmanifest'))
m['name']='Splatbox BETA'; m['short_name']='Splatbox BETA'; m['id']='./'; m['start_url']='./'; m['scope']='./'
json.dump(m,open('beta/manifest.webmanifest','w'),indent=1)
P
}
case "${1:-}" in
 test) tests;;
 beta)
  tests; mkdir -p beta
  cp app/index.html app/sw.js beta/; cp icon-192.png icon-512.png beta/; mkbeta_manifest
  echo "BETA is now Version $(ver beta/index.html). Root is still Version $(ver index.html)."
  echo "Next: git add -A && git commit && git tag -f beta-v$(ver beta/index.html) && git push --tags";;
 stable)
  tests; cp app/index.html app/sw.js .
  echo "STABLE is now Version $(ver index.html)."
  echo "Next: git add -A && git commit && git tag v$(ver index.html) && git push --tags";;
 promote)
  [ -f beta/index.html ] || { echo "no beta to promote"; exit 1; }
  cmp -s beta/index.html app/index.html || { echo "beta differs from app/ - run ./release.sh beta again first"; exit 1; }
  cp beta/index.html beta/sw.js .
  echo "STABLE is now Version $(ver index.html) (promoted from beta)."
  echo "Next: git add -A && git commit && git tag v$(ver index.html) && git push --tags";;
 rollback)
  t="${2:?usage: ./release.sh rollback v018}"
  git rev-parse -q --verify "refs/tags/$t" >/dev/null || { echo "no such tag: $t"; git tag; exit 1; }
  git checkout "$t" -- index.html sw.js
  echo "Root is back to $t (Version $(ver index.html)). Projects saved in a newer format will be refused by it, not damaged."
  echo "Next: git commit -am 'Rollback to $t' && git push";;
 *) sed -n 2,9p "$0";;
esac
