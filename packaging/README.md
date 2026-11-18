# Stand-alone packaging

Scripts and metadata used by [`.github/workflows/build-executable.yml`](../.github/workflows/build-executable.yml)
to produce downloadable Activity Browser builds for Windows, macOS, and Linux.

## Maintainer workflow

```text
rebase packaging branch onto major/beta
        │
        ▼
push packaging branch  ──►  Build Executable (artifacts)
        │
        ▼
Actions → "Release Stand-alone"  ──►  GitHub Release tag `stand-alone`
        │
        ▼
stable download URLs used by README / docs buttons
```

1. **Use the packaging branch** `standalone` (preferred long-term name).  
   Until that branch exists, pushes to `cursor/standalone-downloads-b6ac` also trigger builds.
2. **Rebase** that branch onto the code you want to package (`major` or `beta`).
3. **Push** the packaging branch → **Build Executable** uploads Win/macOS/Linux artifacts.
4. **Promote:** Actions → **Release Stand-alone** → **Run workflow**  
   (optional: paste a Build Executable run ID; otherwise uses the latest success on the packaging branch).  
   This updates the GitHub Release tag [`stand-alone`](https://github.com/LCA-ActivityBrowser/activity-browser/releases/tag/stand-alone)
   with stable asset names so README/docs download buttons keep working.

### Enabling “Run workflow” in the Actions UI

GitHub only shows **workflow_dispatch** in the Actions UI for workflows that exist on the
**default branch** (`main`). The packaging branch alone is not enough for the button.

One-time (or after workflow edits): merge/cherry-pick these files onto `main`:

- `.github/workflows/build-executable.yml`
- `.github/workflows/release-standalone.yml`

Until then you can still dispatch from a machine with `gh`:

```bash
gh workflow run "Build Executable" --ref main \
  -f packaging_ref=cursor/standalone-downloads-b6ac

gh workflow run "Release Stand-alone" --ref main \
  -f packaging_branch=cursor/standalone-downloads-b6ac
```

(`--ref` must point at a commit that contains the workflow file.)

## Versioning

| Where | Format | Example |
|---|---|---|
| About / console / installer version | `{PyPI}-stand-alone` | `3.0.0b202611151932-stand-alone` |
| Package metadata (`setup.py` `VERSION`) | `{PyPI}+stand.alone` (PEP 440) | `3.0.0b202611151932+stand.alone` |
| Stable Release assets (download buttons) | fixed names under tag `stand-alone` | `ActivityBrowser-stand-alone-windows-x64-setup.exe` |
| Versioned Release assets (archival) | include display version | `ActivityBrowser-3.0.0b…-stand-alone-windows-x64-setup.exe` |

`Build Executable` and `Release Stand-alone` default the base version to the latest
`activity-browser` on PyPI. Override with the `ab_version` workflow input when packaging
a commit that is ahead of (or behind) PyPI.

## Outputs

| Platform | Versioned CI artifact | Stable Release asset |
|---|---|---|
| Windows | `ActivityBrowser-<ver>-stand-alone-windows-x64-setup.exe` | `ActivityBrowser-stand-alone-windows-x64-setup.exe` |
| macOS (Apple Silicon) | `…-macos-arm64.dmg` | `ActivityBrowser-stand-alone-macos-arm64.dmg` |
| Linux | `…-linux-x86_64.AppImage` | `ActivityBrowser-stand-alone-linux-x86_64.AppImage` |

Public download URLs (stable):

- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-windows-x64-setup.exe
- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-macos-arm64.dmg
- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-linux-x86_64.AppImage

## Windows multiprocessing (freeze_support)

PyInstaller’s entry script is [`run-activity-browser.py`](../run-activity-browser.py).
On Windows, `multiprocessing.Pool` (metadata load, ecoinvent import, …) spawns
child processes that re-exec that script. The entry’s
`if __name__ == "__main__"` block must call `multiprocessing.freeze_support()`
**before** starting the GUI; otherwise each worker opens a new Activity Browser
window. `activity_browser.run_activity_browser()` also calls `freeze_support()`
as a backstop. Do not move the PyInstaller `Analysis` entry away from that
script without keeping the same guard.

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

## Windows browser / SmartScreen warnings

Stand-alone Windows builds are **not code-signed**. Browsers (Firefox Safe
Browsing, Chrome, Edge) and Windows SmartScreen often flag new unsigned
`.exe` / `.zip` downloads — especially from GitHub Actions artifact URLs
(`*.blob.core.windows.net`). That is a reputation/heuristic false positive,
not evidence the build is malicious.

Mitigations in this repo:
- PyInstaller **UPX is disabled** (UPX-packed binaries are frequent false positives).
- Prefer publishing via the **`stand-alone` GitHub Release** (stable URLs above).
- Longer term: Authenticode signing with a Windows code-signing certificate.

Until then, document for users: download from the official GitHub org Release,
and if the browser blocks it use “Keep” / “Download anyway”, then SmartScreen
“More info” → “Run anyway” if needed.
