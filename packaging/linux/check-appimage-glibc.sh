#!/usr/bin/env bash
# Fail if a Linux AppImage bundles shared libs that need glibc newer than the
# Ubuntu 22.04 baseline (2.35). Catches host-lib over-collection on newer
# runners (see #1818: libglib requiring GLIBC_2.43 → QtBindingsNotFoundError).
set -euo pipefail

APPIMAGE="${1:?Usage: check-appimage-glibc.sh path/to/AppImage}"
MAX_GLIBC="${MAX_GLIBC:-2.35}"

if [[ ! -f "$APPIMAGE" ]]; then
  echo "Missing AppImage: $APPIMAGE" >&2
  exit 1
fi

WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

chmod +x "$APPIMAGE"
# Avoid FUSE on CI runners.
export APPIMAGE_EXTRACT_AND_RUN=1
(
  cd "$WORKDIR"
  "$APPIMAGE" --appimage-extract >/dev/null
)

ROOT="$(find "$WORKDIR" -type d -name _internal | head -n 1)"
if [[ -z "$ROOT" ]]; then
  echo "FAIL: no _internal directory inside AppImage" >&2
  exit 1
fi

python3 - "$ROOT" "$MAX_GLIBC" <<'PY'
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
max_glibc = tuple(int(p) for p in sys.argv[2].split("."))
pat = re.compile(r"GLIBC_([0-9]+(?:\.[0-9]+)*)")
offenders = []

for lib in sorted(root.rglob("*.so*")):
    if not lib.is_file() or lib.is_symlink():
        continue
    try:
        out = subprocess.check_output(
            ["objdump", "-T", str(lib)],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        continue
    versions = []
    for match in pat.finditer(out):
        versions.append(tuple(int(p) for p in match.group(1).split(".")))
    if not versions:
        continue
    needed = max(versions)
    if needed > max_glibc:
        label = "GLIBC_" + ".".join(map(str, needed))
        offenders.append((needed, lib.relative_to(root), label))

if offenders:
    print(
        f"FAIL: AppImage shared libs require glibc newer than {'.'.join(map(str, max_glibc))}:",
        file=sys.stderr,
    )
    for needed, rel, label in sorted(offenders)[:30]:
        print(f"  {rel}: needs {label}", file=sys.stderr)
    if len(offenders) > 30:
        print(f"  ... and {len(offenders) - 30} more", file=sys.stderr)
    print(
        "Build the Linux AppImage on ubuntu-22.04 (or older) so bundled host "
        "libs stay within the glibc 2.35 baseline (#1818).",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"OK: no bundled lib requires glibc newer than {'.'.join(map(str, max_glibc))}")
PY
