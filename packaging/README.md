# Stand-alone packaging

Scripts and metadata used by `.github/workflows/build-executable.yml` to produce
downloadable Activity Browser builds for Windows, macOS, and Linux.

The workflow is started **manually** (Actions → Build Executable → Run workflow).
Pick the branch to build (for example a feature branch that already has this
workflow, or `major` after merge).

## Outputs

| Platform | Artifact |
|---|---|
| Windows | `ActivityBrowser-<version>-windows-x64-setup.exe` (Inno Setup) |
| macOS (Apple Silicon) | `ActivityBrowser-<version>-macos-arm64.dmg` (unsigned) |
| Linux | `ActivityBrowser-<version>-linux-x86_64.AppImage` |

Each build also produces `ActivityBrowser-<version>-<platform>-dependencies.txt`
listing the Python packages resolved at build time (documentation only; the
binary already embeds those packages via PyInstaller).

`<version>` is `YYYYMMDD-<shortsha>` from the CI commit.

## Layout

- `export-dependencies.sh` — write the freeze `.txt`
- `windows/activity-browser.iss` — Inno Setup installer (shows `LICENSE.txt`)
- `macos/create-dmg.sh` — unsigned DMG + Gatekeeper README
- `linux/create-appimage.sh` — AppImage wrapper around the PyInstaller onedir
- `linux/activity-browser.desktop` — desktop entry for the AppImage

## Maintainer: publish to GitHub Releases

CI uploads artifacts only. Publishing is manual:

1. In GitHub Actions, run **Build Executable** on the branch/commit you want.
2. Open that successful run and download the three platform artifacts (and dependency `.txt` files).
3. Create or edit a [GitHub Release](https://github.com/LCA-ActivityBrowser/activity-browser/releases) and attach the files.
4. Mention in the release notes that macOS builds are **unsigned** (see user docs).

Do not rely on Actions artifact retention for long-term distribution — promote
builds you care about to Releases promptly.
