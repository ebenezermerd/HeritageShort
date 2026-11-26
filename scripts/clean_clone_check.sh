#!/usr/bin/env bash
# Proves "clone, run one command, get the film": clones the committed repo into a temp folder,
# runs `make setup film`, and fails unless both MP4s are 60 to 90 seconds and the build made no
# model call. The chosen pictures, narration and score are committed under assets/, so a clean
# clone rebuilds the submitted film from them without any key.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
git clone -q "$SRC" "$TMP/repo"
cd "$TMP/repo"
before=$(wc -l < runs.jsonl)
make setup
make film
for f in outputs/final_9x16.mp4 outputs/final_16x9.mp4; do
  secs=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  awk -v s="$secs" -v f="$f" 'BEGIN { if (s < 60 || s > 90) { print f ": " s " s is outside 60 to 90"; exit 1 } else print f ": " s " s ok" }'
done
calls=$(tail -n +"$((before + 1))" runs.jsonl | { grep -v '"provider": "ffmpeg"' || true; } | wc -l | tr -d ' ')
if [ "$calls" != "0" ]; then
  echo "the build made $calls model calls; a clean clone should make none"
  tail -n +"$((before + 1))" runs.jsonl | grep -v '"provider": "ffmpeg"'
  exit 1
fi
echo "clean clone OK in $TMP/repo: both films built, no model calls"
