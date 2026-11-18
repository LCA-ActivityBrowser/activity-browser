# Stand-alone packaging

Scripts and metadata used by [`.github/workflows/build-executable.yml`](../.github/workflows/build-executable.yml)
to produce downloadable Activity Browser builds for Windows, macOS, and Linux.

## Maintainer workflow

Normal development path is unchanged:

```text
feature branch  →  PR into major  →  (later) major → beta
                         │
                         ▼
              Build Executable (CI artifacts)
                         │
                         ▼
         Actions → "Release Stand-alone" (manual)
                         │
                         ▼
         GitHub Release tag `stand-alone` (public downloads)
```

1. Open a PR into **`major`** (or merge to `major`). **Build Executable** runs automatically.
2. When you want public downloads: Actions → **Release Stand-alone** → **Run workflow**.
   - Branch dropdown: choose **`major`** (not `main`) so GitHub uses the full workflow.
   - Optional: paste a Build Executable run ID; otherwise uses the latest success on `major`.
3. That updates Release tag [`stand-alone`](https://github.com/LCA-ActivityBrowser/activity-browser/releases/tag/stand-alone)
   with stable asset names used by README / docs download buttons.

### Enabling “Run workflow” on main (one-time)

GitHub only shows the Actions **Run workflow** button for `workflow_dispatch` workflows
that exist on the **default branch** (`main`). Put **minimal stubs** there (same
`name:` / filename as the full workflows on `major`) — see PR #1791:

- `.github/workflows/build-executable.yml` — stub with `on: workflow_dispatch` only
- `.github/workflows/release-standalone.yml` — same pattern

When you run them, pick **`major`** in the branch dropdown. GitHub then executes the
full workflow file from that branch. Running against `main` itself only prints a reminder.

## Versioning

| Where | Format | Example |
|---|---|---|
| About / console / installer version | `{PyPI}-stand-alone` | `3.0.0b202611151932-stand-alone` |
| Package metadata (`setup.py` `VERSION`) | `{PyPI}+stand.alone` (PEP 440) | `3.0.0b202611151932+stand.alone` |
| Stable Release assets (download buttons) | fixed names under tag `stand-alone` | `ActivityBrowser-stand-alone-windows-x64-setup.exe` |
| Versioned Release assets (archival) | include display version | `ActivityBrowser-3.0.0b…-stand-alone-windows-x64-setup.exe` |

Override the PyPI base with the `ab_version` workflow input when needed.

## Outputs

| Platform | Stable Release asset |
|---|---|
| Windows | `ActivityBrowser-stand-alone-windows-x64-setup.exe` |
| macOS (Apple Silicon) | `ActivityBrowser-stand-alone-macos-arm64.dmg` |
| Linux | `ActivityBrowser-stand-alone-linux-x86_64.AppImage` |

Public download URLs (stable):

- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-windows-x64-setup.exe
- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-macos-arm64.dmg
- https://github.com/LCA-ActivityBrowser/activity-browser/releases/download/stand-alone/ActivityBrowser-stand-alone-linux-x86_64.AppImage

## Windows multiprocessing (freeze_support)

PyInstaller’s entry script is [`run-activity-browser.py`](../run-activity-browser.py).
On Windows, `multiprocessing.Pool` spawns child processes that re-exec that script.
The entry’s `if __name__ == "__main__"` block must call `multiprocessing.freeze_support()`
before starting the GUI. See also `activity_browser.run_activity_browser()`.

## Fast sparse solver (Windows / Linux x86_64)

AB uses Brightway’s `bw2calc`, which prefers **pypardiso** (Intel MKL) on x86_64.
The PyInstaller spec bundles MKL/OpenMP libs into the onedir tree. CI fails if they
are missing. macOS Apple Silicon uses scikit-umfpack when available.

## Layout

- `export-dependencies.sh` — write the freeze `.txt`
- `windows/activity-browser.iss` — Inno Setup installer
- `macos/create-dmg.sh` — unsigned DMG + Gatekeeper README
- `linux/create-appimage.sh` — AppImage wrapper
- `linux/activity-browser.desktop` — desktop entry for the AppImage

## Windows browser / SmartScreen warnings

Builds are **not code-signed**. Prefer the official `stand-alone` GitHub Release links;
browser/SmartScreen warnings on unsigned `.exe` files are common false positives.
