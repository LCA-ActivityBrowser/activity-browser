# Packaging

In-repo build inputs for shipping Activity Browser. Install channels (**pip**, **conda**, **stand-alone**) are defined in `CONTEXT.md`; this tree holds the conda and stand-alone build material. Freeze entrypoints (`pyinstaller.spec`, `run-activity-browser.py`) and the legacy `setup.py` shim stay at the repository root.

| Path | Role |
|---|---|
| [`conda/`](conda/) | Conda-build recipe (`meta.yaml`) used by deploy CI / `lca` channel builds |
| `windows/`, `macos/`, `linux/` | Stand-alone installer / DMG / AppImage scripts |
| `smoke-standalone.sh`, `export-dependencies.sh` | Stand-alone CI helpers |

The public **conda-forge** recipe remains in the [activity-browser-feedstock](https://github.com/conda-forge/activity-browser-feedstock). There is no root `recipe/` stub — use `packaging/conda/`.

---

# Stand-alone packaging

Scripts and metadata used by [`.github/workflows/build-executable.yml`](../.github/workflows/build-executable.yml)
to produce downloadable Activity Browser builds for Windows, macOS, and Linux.

## Maintainer workflow

Normal development path is unchanged:

```text
feature → PR into dev → (later) PR: dev → main
                                      │
                                      ▼
                           Build Executable (CI artifacts)
                                      │
                                      ▼
                      Actions → "Release Stand-alone" (manual)
                                      │
                                      ▼
                      GitHub Release tag `{AB}-stand-alone` (immutable)
```

1. **Build Executable** runs automatically on PRs into **`main`**. For an ad-hoc build (e.g. before a stand-alone cut), Actions → **Build Executable** → **Run workflow** and pick branch **`dev`**.
2. When you want public downloads: Actions → **Release Stand-alone** → **Run workflow**.
   - Branch dropdown: choose **`dev`** (not `main`) so GitHub uses the full workflow.
   - Optional: paste a Build Executable run ID; otherwise uses the latest success on `dev`.
3. That creates an immutable Release tagged `{PyPI}-stand-alone` with versioned installer assets.
   Docs and the in-app updater point users at the [Releases](https://github.com/LCA-ActivityBrowser/activity-browser/releases) page (newest `*-stand-alone` tag). See ADR-0015.

### Enabling “Run workflow” on main (one-time)

GitHub only shows the Actions **Run workflow** button for `workflow_dispatch` workflows
that exist on the **default branch** (`main`). Put **minimal stubs** there (same
`name:` / filename as the full workflows on `dev`) — see PR #1791:

- `.github/workflows/build-executable.yml` — stub with `on: workflow_dispatch` only
- `.github/workflows/release-standalone.yml` — same pattern

When you run them, pick **`dev`** in the branch dropdown. GitHub then executes the
full workflow file from that branch. Running against `main` itself only prints a reminder.

## Versioning

| Where | Format | Example |
|---|---|---|
| Package metadata (`setup.py` `VERSION`) | same as PyPI AB version | `3.0.0b202611151932` |
| About / console / installer display | `{PyPI}-stand-alone` | `3.0.0b202611151932-stand-alone` |
| GitHub Release tag | `{PyPI}-stand-alone` | `3.0.0b202611151932-stand-alone` |
| Versioned Release assets | include display version | `ActivityBrowser-3.0.0b…-stand-alone-windows-x64-setup.exe` |

Stand-alone is detected at runtime with `sys.frozen`, not a PEP 440 local version label.

Override the PyPI base with the `ab_version` workflow input when needed.

## Outputs

| Platform | Versioned Release asset |
|---|---|
| Windows | `ActivityBrowser-{ver}-stand-alone-windows-x64-setup.exe` |
| macOS (Apple Silicon) | `ActivityBrowser-{ver}-stand-alone-macos-arm64.dmg` |
| Linux | `ActivityBrowser-{ver}-stand-alone-linux-x86_64.AppImage` |

Public entry point: [Releases](https://github.com/LCA-ActivityBrowser/activity-browser/releases) (choose a `*-stand-alone` tag).

## Windows multiprocessing (freeze_support)

PyInstaller’s entry script is [`run-activity-browser.py`](../run-activity-browser.py).
On Windows, `multiprocessing.Pool` spawns child processes that re-exec that script.
The entry’s `if __name__ == "__main__"` block must call `multiprocessing.freeze_support()`
before starting the GUI. See also `activity_browser.run_activity_browser()`.

## macOS console / LSBackgroundOnly

`pyinstaller.spec` uses `console=False` on darwin (and sets `LSBackgroundOnly` to
false in the bundle plist). `console=True` makes PyInstaller mark the `.app` as
background-only; Finder then opens Terminal/bash after the splash. Build Executable
CI asserts the built plist is not `LSBackgroundOnly=true`.

## macOS Qt WebEngine support

Creating a `QWebEnginePage` aborts if `Helpers` (QtWebEngineProcess) or
`Resources` (`icudtl.dat` / `.pak`) are missing from
`QtWebEngineCore.framework`. The spec copies both into the `.app` after BUNDLE;
CI checks they are present.

## Linux AppImage glibc baseline

Build on **`ubuntu-22.04`** (glibc **2.35**) so the AppImage runs on current
LTS desktops. `ubuntu-latest` can bundle host libs that need a newer glibc and
fail elsewhere as `QtBindingsNotFoundError` (#1818).

## Smoke launch (CI)

After packaging, Build Executable runs [`smoke-standalone.sh`](smoke-standalone.sh):
silent-install the Windows `.exe` (or launch the macOS `.app` binary / Linux
AppImage), start under `QT_QPA_PLATFORM=offscreen` with
`AB_SKIP_SETTINGS_ON_STARTUP` / `--no-checks`, and fail if the process exits in
the first ~90s or if the console line `Activity Browser version:` does not
exactly match `AB_VERSION` (the `{PyPI}-stand-alone` stamp). This catches
splash-then-crash failures and wrong version stamps; it does not cover
Gatekeeper / SmartScreen Finder UX.

## Fast sparse solver

AB uses Brightway’s `bw2calc`, which prefers **pypardiso** (Intel MKL) on x86_64 and
**scikit-umfpack** (SuiteSparse) on Apple Silicon.

| Platform | Freeze env | Solver | CI |
|---|---|---|---|
| Windows / Linux x86_64 | `uv` | pypardiso + MKL (pip) | Fails if `mkl_rt` missing |
| macOS Apple Silicon | micromamba (conda-forge) | scikit-umfpack + SuiteSparse | Fails if umfpack + core SuiteSparse libs missing from env or `.app` |

The PyInstaller spec bundles the matching native libs into the onedir / `.app` tree.
Win/Linux stay on `uv` because MKL wheels are straightforward there; Mac uses micromamba
because `scikit-umfpack` is sdist-only on PyPI. See ADR-0016.

## Layout

- `export-dependencies.sh` — write the freeze `.txt`
- `windows/activity-browser.iss` — Inno Setup installer
- `macos/create-dmg.sh` — unsigned DMG + Gatekeeper README
- `linux/create-appimage.sh` — AppImage wrapper
- `linux/activity-browser.desktop` — desktop entry for the AppImage

## Windows upgrade leftovers

The Windows installer deletes `{app}\_internal` (and the main exe) before copying the
new onedir tree. Without that, reinstalling over an older stand-alone can leave
stale `activity_browser-*.dist-info` folders; `importlib.metadata` may then report
an old build id in the console even though Apps → Installed apps shows the new
stamp. macOS DMGs replace the whole `.app`, so they do not have this issue.

## Windows browser / SmartScreen warnings

Builds are **not code-signed**. Prefer official GitHub Releases (`*-stand-alone` tags);
browser/SmartScreen warnings on unsigned `.exe` files are common false positives.
