# Stand-alone packaging

Scripts and metadata used by [`.github/workflows/build-executable.yml`](../.github/workflows/build-executable.yml)
to produce downloadable Activity Browser builds for Windows, macOS, and Linux.

## Maintainer workflow

Intended loop for shipping stand-alone builds:

1. **Use the packaging branch** `standalone` (preferred long-term name).  
   Until that branch exists, pushes to `cursor/standalone-downloads-b6ac` also trigger builds.
2. **Rebase** that branch onto the code you want to package:
   - `major` — current development integration branch  
   - `beta` — what is published to PyPI / conda  
3. **Push** the packaging branch. CI runs **Build Executable** and uploads
   Windows / macOS / Linux artifacts.
4. **Promote manually:** download artifacts from the Actions run and attach them
   to a [GitHub Release](https://github.com/LCA-ActivityBrowser/activity-browser/releases)
   (create or update a release; do not rely on Actions artifact retention).

Optional: **Actions → Build Executable → Run workflow** (`workflow_dispatch`) if
the workflow file is available on the repo default branch and you can pick the
packaging branch in the UI. Push-to-packaging-branch is the supported path.

```text
major or beta  --rebase-->  standalone  --push-->  Actions artifacts  --manual-->  GitHub Release
```

## Outputs

| Platform | Artifact |
|---|---|
| Windows | `ActivityBrowser-<version>-windows-x64-setup.exe` (Inno Setup) |
| macOS (Apple Silicon) | `ActivityBrowser-<version>-macos-arm64.dmg` (unsigned; console enabled) |
| Linux | `ActivityBrowser-<version>-linux-x86_64.AppImage` |

Each build also produces `ActivityBrowser-<version>-<platform>-dependencies.txt`
listing the Python packages resolved at build time (documentation only; the
binary already embeds those packages via PyInstaller).

`<version>` is `YYYYMMDD-<shortsha>` from the CI commit.

## Fast sparse solver (Windows / Linux x86_64)

AB uses Brightway’s `bw2calc`, which prefers **pypardiso** (Intel MKL) on x86_64.
`pyproject.toml` already depends on `pypardiso` on Windows; the PyInstaller spec
bundles the pip `mkl` / OpenMP shared libraries into the onedir tree at
`Library/bin` (Windows) or `lib` (Linux) so pypardiso can find `mkl_rt` after
freeze. CI fails the build if those libs are missing.

macOS Apple Silicon uses scikit-umfpack when available (pypardiso is not on ARM).

## Layout

- `export-dependencies.sh` — write the freeze `.txt`
- `windows/activity-browser.iss` — Inno Setup installer (shows `LICENSE.txt`)
- `macos/create-dmg.sh` — unsigned DMG + Gatekeeper README
- `linux/create-appimage.sh` — AppImage wrapper around the PyInstaller onedir
- `linux/activity-browser.desktop` — desktop entry for the AppImage

## Publishing checklist

1. Open the successful **Build Executable** run for the push you care about.
2. Download the three platform artifacts (and dependency `.txt` files).
3. Create or edit a GitHub Release and attach the files.
4. Note in the release body that macOS builds are **unsigned** (Gatekeeper:
   Control-click → Open).
5. Point the repo README / install docs at that Release (or `/releases/latest`)
   once you are ready for users to find the downloads on the landing page.
