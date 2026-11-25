#!/usr/bin/env bash
# Proves "clone, run one command, get the film": clones the committed repo into a temp folder,
# copies only .env, runs `make setup film`, and fails unless both MP4s are 60-90 seconds.
# Uses real Cloudflare image calls (about 20), so run it sparingly.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
git clone -q "$SRC" "$TMP/repo"
cp "$SRC/.env" "$TMP/repo/.env"
cd "$TMP/repo"
make setup
make film VOICE="${VOICE:-say}"
for f in outputs/final_9x16.mp4 outputs/final_16x9.mp4; do
  secs=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  awk -v s="$secs" -v f="$f" 'BEGIN { if (s < 60 || s > 90) { print f ": " s " s is outside 60-90"; exit 1 } else print f ": " s " s ok" }'
done
echo "clean clone OK in $TMP/repo"
