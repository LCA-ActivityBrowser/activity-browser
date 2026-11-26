#!/usr/bin/env bash
# Keep the AppImage within Ubuntu 22.04's glibc (2.35). Newer CI images can
# bundle host libs that need GLIBC_2.43+ and break on common desktops (#1818).
set -euo pipefail

APPIMAGE="${1:?Usage: $0 path/to/AppImage}"
MAX_GLIBC="${MAX_GLIBC:-2.35}"
[[ -f "$APPIMAGE" ]] || { echo "Missing AppImage: $APPIMAGE" >&2; exit 1; }

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
chmod +x "$APPIMAGE"
(
  cd "$WORKDIR"
  APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE" --appimage-extract >/dev/null
)
ROOT="$(find "$WORKDIR" -type d -name _internal | head -n 1)"
[[ -n "$ROOT" ]] || { echo "FAIL: no _internal in AppImage" >&2; exit 1; }

HIGHEST="$(
  find "$ROOT" -type f -name '*.so*' -print0 \
    | xargs -0 -r -n1 objdump -T 2>/dev/null \
    | grep -oE 'GLIBC_[0-9]+(\.[0-9]+)*' \
    | sort -Vu \
    | tail -n 1
)"
NEED="${HIGHEST#GLIBC_}"
if [[ -n "$NEED" && "$(printf '%s\n' "$MAX_GLIBC" "$NEED" | sort -V | tail -n 1)" != "$MAX_GLIBC" ]]; then
  echo "FAIL: AppImage needs $HIGHEST (baseline is GLIBC_$MAX_GLIBC). Build on ubuntu-22.04 (#1818)." >&2
  exit 1
fi
echo "OK: AppImage glibc ≤ $MAX_GLIBC${HIGHEST:+ (max $HIGHEST)}"
