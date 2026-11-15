#!/usr/bin/env bash
# Section map of app/index.html, generated from the /* ---------- ... ---------- */ markers, so it never goes stale.
# Use:  tools/map.sh            whole map
#       tools/map.sh timeline   only sections whose title matches
#       then read just that range:  sed -n 'START,ENDp' app/index.html
cd "$(dirname "$0")/.."
f=app/index.html
total=$(wc -l < "$f")
grep -n '^/\* ----------' "$f" | cut -c1-110 | awk -F: -v total="$total" -v pat="${1:-}" '
  { n[NR]=$1; t[NR]=$0; sub(/^[0-9]+:/,"",t[NR]) }
  END { for(i=1;i<=NR;i++){ e=(i<NR)?n[i+1]-1:total; if(pat==""||tolower(t[i])~tolower(pat)) printf "%5d-%-5d %s\n", n[i], e, t[i] } }'
