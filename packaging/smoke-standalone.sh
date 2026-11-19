#!/usr/bin/env bash
# Smoke-test a just-built stand-alone: launch under offscreen Qt and require
# the process to stay alive long enough to pass the splash / Brightway load.
# Usage (from repo root): packaging/smoke-standalone.sh
# Needs AB_VERSION in the environment (same stamp as Build Executable).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

AB_VERSION="${AB_VERSION:?AB_VERSION must be set (e.g. 3.0.0b…-stand-alone)}"
SMOKE_SECONDS="${SMOKE_SECONDS:-90}"
LOG="${ROOT}/dist/smoke-standalone.log"
mkdir -p "${ROOT}/dist"
rm -f "$LOG"

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export AB_SKIP_SETTINGS_ON_STARTUP="${AB_SKIP_SETTINGS_ON_STARTUP:-1}"
export AB_NO_SEARCHER="${AB_NO_SEARCHER:-1}"
# Ensure the version print reaches the smoke log under redirection.
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
# Keep Brightway / settings out of the runner home where possible.
export HOME="${ROOT}/dist/smoke-home"
mkdir -p "$HOME"

resolve_binary() {
  case "$(uname -s)" in
    Linux*)
      local appimage="dist/installers/ActivityBrowser-${AB_VERSION}-linux-x86_64.AppImage"
      if [[ ! -f "$appimage" ]]; then
        echo "Missing AppImage: $appimage" >&2
        exit 1
      fi
      chmod +x "$appimage"
      # Avoid FUSE on GitHub-hosted runners.
      export APPIMAGE_EXTRACT_AND_RUN=1
      printf '%s' "$appimage"
      ;;
    Darwin*)
      local bin="dist/Activity Browser.app/Contents/MacOS/activity-browser"
      if [[ ! -x "$bin" ]]; then
        echo "Missing macOS app binary: $bin" >&2
        exit 1
      fi
      printf '%s' "$bin"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      local setup="dist/installers/ActivityBrowser-${AB_VERSION}-windows-x64-setup.exe"
      local dest="${ROOT}/dist/smoke-install"
      if [[ ! -f "$setup" ]]; then
        echo "Missing Windows installer: $setup" >&2
        exit 1
      fi
      rm -rf "$dest"
      mkdir -p "$dest"
      # Inno: silent install into the workspace (PrivilegesRequired=lowest).
      "$setup" //VERYSILENT //NORESTART //SUPPRESSMSGBOXES //DIR="$(cygpath -w "$dest" 2>/dev/null || echo "$dest")"
      local bin="${dest}/activity-browser.exe"
      if [[ ! -f "$bin" ]]; then
        echo "Installer finished but missing: $bin" >&2
        exit 1
      fi
      # Guard against upgrade leftovers: only one activity_browser dist-info.
      local infos
      infos="$(find "$dest/_internal" -maxdepth 1 -type d -name 'activity_browser-*.dist-info' 2>/dev/null | wc -l | tr -d ' ')"
      if [[ "${infos}" != "1" ]]; then
        echo "FAIL: expected exactly one activity_browser-*.dist-info under _internal, found ${infos}:" >&2
        find "$dest/_internal" -maxdepth 1 -type d -name 'activity_browser-*.dist-info' -print >&2 || true
        exit 1
      fi
      printf '%s' "$bin"
      ;;
    *)
      echo "Unsupported OS for smoke-standalone: $(uname -s)" >&2
      exit 1
      ;;
  esac
}

BIN="$(resolve_binary)"
echo "Smoke-launching: $BIN (alive for ${SMOKE_SECONDS}s)"
echo "Env: QT_QPA_PLATFORM=$QT_QPA_PLATFORM AB_SKIP_SETTINGS_ON_STARTUP=$AB_SKIP_SETTINGS_ON_STARTUP"

"$BIN" --no-checks >"$LOG" 2>&1 &
PID=$!

cleanup() {
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

for ((i = 1; i <= SMOKE_SECONDS; i++)); do
  if ! kill -0 "$PID" 2>/dev/null; then
    status=0
    wait "$PID" || status=$?
    echo "FAIL: process exited after ${i}s (status=${status})" >&2
    echo "----- $LOG -----" >&2
    tail -n 200 "$LOG" >&2 || true
    exit 1
  fi
  if grep -Eq 'Building main window|Successfully loaded|Activity Browser version:' "$LOG" 2>/dev/null; then
    # Still require a short settle so splash→main is not a flash-and-die.
    if (( i >= 15 )); then
      # Package / installer stamp must match the CI display version (e.g. not a
      # leftover YYYYMMDD+sha build id from an older packaging scheme).
      if ! grep -Fq "Activity Browser version: ${AB_VERSION}" "$LOG"; then
        echo "FAIL: expected console version '${AB_VERSION}'" >&2
        echo "----- $LOG -----" >&2
        grep -E 'Activity Browser version:' "$LOG" >&2 || true
        tail -n 50 "$LOG" >&2 || true
        exit 1
      fi
      echo "OK: process alive ${i}s; version ${AB_VERSION}; log shows startup progress"
      exit 0
    fi
  fi
  sleep 1
done

if ! grep -Fq "Activity Browser version: ${AB_VERSION}" "$LOG"; then
  echo "FAIL: expected console version '${AB_VERSION}' after ${SMOKE_SECONDS}s" >&2
  echo "----- $LOG -----" >&2
  grep -E 'Activity Browser version:' "$LOG" >&2 || true
  tail -n 50 "$LOG" >&2 || true
  exit 1
fi

echo "OK: process stayed alive for ${SMOKE_SECONDS}s; version ${AB_VERSION}"
exit 0
