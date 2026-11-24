# Activity Browser — Agent Guide

This repository is a Qt (PySide6/qtpy) desktop GUI for Life Cycle Assessment on Brightway2.

**Start here for how agent docs are organized:** [`.agents/README.md`](.agents/README.md).

Be concise and actionable. Prefer small, localized changes. Large refactors need human review.

## Agent skills

### Issue tracker

Local markdown under `.scratch/` (gitignored). See `.agents/issue-tracker.md`.

### Triage labels

Default Matt Pocock triage roles. See `.agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `adr/`. See `.agents/domain.md`.

### Development workflow

New work is sized **S / M / L**. See `.cursor/rules/development-workflow.mdc`. If unsure which tier, ask the user. For M/L, pause and ask the user to invoke the next slash skill (`/grill-with-docs`, `/to-spec`, `/to-tickets`, `/implement`, `/code-review`) rather than improvising those steps.

## Key facts

- **Entry point:** console script `activity-browser` → `activity_browser:run_activity_browser`; also `python -m activity_browser` / `run-activity-browser.py`.
- **UI toolkit:** Qt via `qtpy` / PySide6. Application class: `activity_browser.ui.core.application.ABApplication`.
- **App singletons:** `from activity_browser import app` then `app.application`, `app.signals`, `app.settings`, `app.metadata`, `app.main_window`.
- **Signals:** `app.signals` (`ABSignals`) mainly bridges bw2data blinker events to Qt. Preferred path: action → Brightway/bwutils → bw signals → UI. See `adr/0003-signals-event-bus.md`.
- **Settings:** `app.settings` (`activity_browser.bwutils.settings.Settings`); prefer this over ad-hoc config files.
- **Metadata:** Prefer `app.metadata` (MetaDataStore) for activity/process labels and tabular lookups. Do not query SQLite (`ActivityDataset`) or `bd.get_node` for display metadata the store already has. Index is `(database, code)`; the `id` column is the Brightway datapackage id. Fallback to Brightway only for writes, missing rows, fields the store does not keep, or a live activity proxy. `bwutils/` helpers should take a dataframe (or lookup callback), not import `app`. See `activity_browser/bwutils/metadata/README.md` and `adr/0005-metadata-from-metadatastore.md`.
- **Brightway:** heavy use of `bw2data`, `bw2calc`, `bw2analyzer`, `bw2io`, etc. Data mutations go through Brightway APIs and must keep signal expectations intact.

## Architecture and placement

| Layer | Path | Role |
|---|---|---|
| **ui/** | `activity_browser/ui/` | Application-agnostic Qt building blocks (widgets, delegates, dialogs, wizards, web views, `core/`). Must not depend on `app` singletons. |
| **app/** | `activity_browser/app/` | Application-aware orchestration: pages, panes, actions, dialogs; wires UI to Brightway and signals. Brightway mutations live mainly in **actions**. |
| **bwutils/** | `activity_browser/bwutils/` | Brightway/scientific logic without Qt UI. Prefer this when logic only needs Brightway. |
| **mod/** | `activity_browser/mod/` | Monkey-patches for upstream libraries. Minimally invasive; document why. |
| **static/** | `activity_browser/static/` | HTML/JS/CSS for WebEngine views (graph explorer, sankey, etc.). |

**Placement rule**

- If logic only depends on Brightway2 → `bwutils/`
- If a widget does not depend on the application being initialized → `ui/`
- Otherwise (needs `app.signals` / settings / metadata / main window) → `app/`

See also ADRs under `adr/` and module READMEs under each package directory.

## Domain language

Use terms from [`CONTEXT.md`](CONTEXT.md). Read relevant ADRs in `adr/` before changing architecture-sensitive areas.

## Plugins (placeholder)

Plugin architecture is being redesigned. Do not harden or invent a plugin API contract here. When the new design is decided, document it in this section, an ADR, and the relevant module README.

## Deferred imports

Startup loads heavy packages in background threads (`activity_browser/__main__.py`). Avoid top-level imports of heavy deps (`PySide6`/`bw2data` stacks beyond what the module already requires) when that would slow tests or break the delayed-import pattern. Prefer imports inside functions or worker threads when following existing patterns.

## Testing

Two common patterns:

1. **Pure logic** (no Qt): import the unit under test and assert — see e.g. `tests/test_uncertainty_preview.py`.
2. **UI / integration:** use `pytest-qt` (`qtbot`), fixtures from `tests/conftest.py` (`main_window`, `basic_database`, …), and `@bw2test` where Brightway project isolation is needed. Wait for metadata loaders (`_wait_for_loader`) and `processEvents` as existing tests do. Env vars such as `AB_SKIP_SETTINGS_ON_STARTUP` and `AB_NO_SEARCHER` are set in `conftest.py` for a reason — preserve that pattern.

Fixtures and sample data live under `tests/fixtures/`. Prefer non-blocking UI tests; monkeypatch blocking dialogs (see `no_exception_dialogs`).

## CI and packaging (pointers)

Agents should not assume Linux-only or a single Python version. Details live in the workflow files; summary:

- **Tests:** `.github/workflows/testing.yaml` — pytest on Ubuntu / Windows / macOS × Python 3.11–3.14; `QT_QPA_PLATFORM=offscreen`; install via `pip install .[testing]`.
- **Stand-alone executables:** `.github/workflows/build-executable.yml` on PR into `main`, or manual dispatch (prefer `dev`). Windows Inno Setup, macOS unsigned DMG, Linux AppImage. Promote via Release Stand-alone — see `packaging/README.md` and ADR-0015.
- **Workflow overview:** `.github/workflows/README.md` (testing, canary, deploy, executables, releases).
- **Branches:** feature work → PR into `dev`; land on stable via `dev` → `main`; public versions via semver tags. See `CONTRIBUTING.md` and ADR-0017.
- **Dev deps / extras:** `pyproject.toml` (`[project.optional-dependencies]`).

## AB docs (`docs/`)

- **Audience / voice:** `docs/` is the GitHub Pages site for **AB users (LCA practitioners)**, not for agents or programmers (ADR-0018).
- **Read** `docs/` when AB or UI behavior matters.
- After behavior-changing work, **check** whether `docs/` needs updating; if yes, edit and **edit-then-flag** (list the `docs/` changes and ask the user to confirm). Ask first only for large rewrites or undecided AB behavior.
- Put implementation / agent detail in `adr/`, `.agents/`, module READMEs, or this file — not in practitioner-facing pages.

## Safety for AI edits

- Small, localized changes preferred.
- When changing stateful behavior (settings, databases, signals), update or add tests and keep the same signal contracts.
- Preserve deferred-import and `mod/` patching patterns unless an ADR says otherwise.
- Do not invent plugin APIs (see placeholder above).
- **Never create a git commit unless the user explicitly asks to commit.** Slash skills that mention committing (e.g. `/implement`) do not override this — leave changes uncommitted until the user requests a commit.

## Useful references

- Domain glossary: `CONTEXT.md`
- Agent docs map: `.agents/README.md`
- ADRs: `adr/`
- AB docs (LCA practitioners): `docs/`
- Contributing / branching: `CONTRIBUTING.md`
- Module notes: `activity_browser/app/README.md`, `ui/README.md`, `bwutils/README.md`, `mod/README.md`
- Tests: `tests/README.md`, `tests/conftest.py`
