#!/usr/bin/env bash
# Copies the latest simulation run into public/data/ so the app can be
# served as a fully static site (e.g. GitHub Pages).
set -euo pipefail

WEBAPP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOGS_DIR="$WEBAPP_DIR/../logs"
OUT_DIR="$WEBAPP_DIR/public/data"

# Pick the latest run directory (alphabetical sort = chronological for our naming)
LATEST_RUN=$(ls -1d "$LOGS_DIR"/run_* 2>/dev/null | sort | tail -1)
if [ -z "$LATEST_RUN" ]; then
  echo "ERROR: No run_* directories found in $LOGS_DIR" >&2
  exit 1
fi
RUN_NAME=$(basename "$LATEST_RUN")
echo "Bundling run: $RUN_NAME"

# Clean and recreate output
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Copy the entire run directory
cp -r "$LATEST_RUN" "$OUT_DIR/$RUN_NAME"

# Create runs.json index (array of run names)
echo "[\"$RUN_NAME\"]" > "$OUT_DIR/runs.json"

echo "Done. Static data written to $OUT_DIR/"
du -sh "$OUT_DIR"
