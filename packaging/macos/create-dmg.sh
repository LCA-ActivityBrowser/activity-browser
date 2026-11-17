#!/usr/bin/env bash
# Create an unsigned DMG containing Activity Browser.app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:?Usage: create-dmg.sh <version>}"
APP_PATH="${ROOT}/dist/Activity Browser.app"
OUT_DIR="${ROOT}/dist/installers"
DMG_NAME="ActivityBrowser-${VERSION}-macos-arm64.dmg"
STAGING="${ROOT}/dist/dmg-staging"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Missing app bundle at: $APP_PATH" >&2
  exit 1
fi

mkdir -p "$OUT_DIR" "$STAGING"
rm -rf "${STAGING:?}/"*
cp -R "$APP_PATH" "$STAGING/"
ln -sf /Applications "$STAGING/Applications"

# Copy dependency freeze next to the app inside the DMG when present.
FREEZE_SRC="${ROOT}/dist/ActivityBrowser-${VERSION}-macos-arm64-dependencies.txt"
if [[ -f "$FREEZE_SRC" ]]; then
  cp "$FREEZE_SRC" "$STAGING/dependencies.txt"
fi

# Gatekeeper note for unsigned builds.
cat >"$STAGING/README-macOS.txt" <<'EOF'
Activity Browser (unsigned macOS build)
=======================================

This DMG is not notarized. On first launch macOS Gatekeeper may block the app.

To open it:
1. Open the DMG and drag "Activity Browser" to Applications (or run from here).
2. In Finder, Control-click (right-click) the app and choose Open.
3. Confirm Open in the dialog.

After that, normal double-clicks should work for this user account.
EOF

rm -f "${OUT_DIR}/${DMG_NAME}"
hdiutil create \
  -volname "Activity Browser" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "${OUT_DIR}/${DMG_NAME}"

echo "Wrote ${OUT_DIR}/${DMG_NAME}"
