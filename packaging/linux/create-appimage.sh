#!/usr/bin/env bash
# Wrap the PyInstaller onedir tree as a Linux AppImage.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:?Usage: create-appimage.sh <version>}"
ONEDIR="${ROOT}/dist/activity-browser"
OUT_DIR="${ROOT}/dist/installers"
APPDIR="${ROOT}/dist/AppDir"
APPIMAGE_NAME="ActivityBrowser-${VERSION}-linux-x86_64.AppImage"

if [[ ! -d "$ONEDIR" ]]; then
  echo "Missing PyInstaller onedir at: $ONEDIR" >&2
  exit 1
fi
if [[ ! -x "${ONEDIR}/activity-browser" ]]; then
  echo "Missing executable ${ONEDIR}/activity-browser" >&2
  exit 1
fi

rm -rf "$APPDIR"
mkdir -p \
  "${APPDIR}/usr/bin" \
  "${APPDIR}/usr/share/applications" \
  "${APPDIR}/usr/share/icons/hicolor/256x256/apps" \
  "${APPDIR}/usr/share/metainfo"

# Ship the whole onedir under usr/lib so relative libs resolve.
mkdir -p "${APPDIR}/usr/lib/activity-browser"
cp -a "${ONEDIR}/." "${APPDIR}/usr/lib/activity-browser/"

cat >"${APPDIR}/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
exec "${HERE}/usr/lib/activity-browser/activity-browser" "$@"
EOF
chmod +x "${APPDIR}/AppRun"

cp "${ROOT}/packaging/linux/activity-browser.desktop" \
  "${APPDIR}/usr/share/applications/activity-browser.desktop"
# AppImage top-level desktop + icon entries
cp "${ROOT}/packaging/linux/activity-browser.desktop" \
  "${APPDIR}/activity-browser.desktop"

ICON_SRC="${ROOT}/activity_browser/static/icons/main/activitybrowser.png"
cp "$ICON_SRC" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/activity-browser.png"
cp "$ICON_SRC" "${APPDIR}/activity-browser.png"

FREEZE_SRC="${ROOT}/dist/ActivityBrowser-${VERSION}-linux-x86_64-dependencies.txt"
if [[ -f "$FREEZE_SRC" ]]; then
  cp "$FREEZE_SRC" "${APPDIR}/usr/lib/activity-browser/dependencies.txt"
fi

if [[ -f "${ROOT}/LICENSE.txt" ]]; then
  cp "${ROOT}/LICENSE.txt" "${APPDIR}/usr/lib/activity-browser/LICENSE.txt"
fi

# AppImages are run by other users; world-readable/executable dirs are required.
chmod -R a+rX "$APPDIR"

mkdir -p "$OUT_DIR"

TOOL_DIR="${ROOT}/dist/appimage-tools"
mkdir -p "$TOOL_DIR"
APPIMAGETOOL="${TOOL_DIR}/appimagetool"
if [[ ! -x "$APPIMAGETOOL" ]]; then
  curl -fsSL -o "$APPIMAGETOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

# Extract appimagetool if FUSE is unavailable (common on CI).
if ! "$APPIMAGETOOL" --appimage-help >/dev/null 2>&1; then
  pushd "$TOOL_DIR" >/dev/null
  "$APPIMAGETOOL" --appimage-extract >/dev/null
  popd >/dev/null
  APPIMAGETOOL="${TOOL_DIR}/squashfs-root/AppRun"
fi

export ARCH=x86_64
"$APPIMAGETOOL" "$APPDIR" "${OUT_DIR}/${APPIMAGE_NAME}"
chmod +x "${OUT_DIR}/${APPIMAGE_NAME}"
echo "Wrote ${OUT_DIR}/${APPIMAGE_NAME}"
