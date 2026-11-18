#!/usr/bin/env bash
# Write a freeze of the build environment next to packaged outputs.
set -euo pipefail

OUT_PATH="${1:?Usage: export-dependencies.sh <output-path>}"
mkdir -p "$(dirname "$OUT_PATH")"

{
  echo "# Activity Browser stand-alone build — bundled dependency versions"
  echo "# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "#"
  if command -v uv >/dev/null 2>&1; then
    echo "# Python: $(uv run --no-sync python -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || python -V 2>&1 || true)"
    echo "#"
    uv pip freeze
  else
    echo "# Python: $(python -V 2>&1 || true)"
    echo "#"
    pip freeze
  fi
} >"$OUT_PATH"

echo "Wrote dependency freeze to $OUT_PATH"
