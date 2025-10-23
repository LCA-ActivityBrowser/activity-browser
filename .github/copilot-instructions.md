This repository is a Qt (PySide6/qtpy) desktop application that acts as a GUI front-end for Brightway2.

Be concise and actionable. Focus on this project's structure, conventions and patterns so an AI coding agent can make safe, small changes.

Key facts (what to know first)
- Entry point: `activity-browser` console script -> `activity_browser:run_activity_browser` and `run-activity-browser.py` / `activity_browser.__main__`.
- UI: Qt via `qtpy`/`PySide6`. The application class is `activity_browser.ui.application.ABApplication` (see `activity_browser/ui/application.py`).
- Signals: project-wide event bus is `activity_browser.signals.signals` which bridges bw2data signals to Qt Signals. Use these for cross-component communication.
- Settings: persistent settings live in `activity_browser/settings.py` (`ab_settings`, `project_settings`) and use platformdirs; prefer using those classes for config/state.
- Brightway integration: heavy use of `bw2data`, `bw2calc`, `bw2analyzer`, `bw2io`, etc. Changes to data models must account for bw2data signals (see `activity_browser/signals.py`).

Project architecture and patterns
- MVC-ish, but UI-heavy: layouts and pages live under `activity_browser/layouts` and `activity_browser/ui`. Widgets, panes and pages are the primary units for UI changes.
- Actions: UI operations are encapsulated in `activity_browser/actions/*`. Inspect `base.py` and concrete actions for how commands are registered and run from menus/toolbars.
- Deferred imports: startup uses threads that import large packages (see `activity_browser/__main__.py` ModuleThread/SettingsThread). Avoid importing heavy modules at module import time to keep tests fast.
- Global shortcuts are registered via `application.global_shortcut` decorator. Setting `application.main_window` attaches them automatically.

Developer workflows (how to run/build/test)
- Run locally (recommended in a virtualenv or conda env matching pyproject dependencies):
  - Install dev deps from `pyproject.toml` or use `pip install -e .[dev]`.
  - Start the app: `python -m activity_browser` or `python run-activity-browser.py` or use `activity-browser` after installing the package.
- Tests: pytest is configured. Run `pytest` from repository root. Test-related extras are in `pyproject.toml` under `[project.optional-dependencies].testing`.
- Packaging: standard setuptools (see `setup.py` and `pyproject.toml`); versioning can be supplied via env vars `VERSION`/`PKG_VERSION` or `GIT_DESCRIBE_TAG`.

Conventions and gotchas
- Prefer using project signals (`activity_browser.signals.signals.*`) instead of directly calling UI functions to update other parts of the app.
- Settings are JSON files persisted per-user via platformdirs; use `ab_settings` and `project_settings` singletons rather than creating custom files.
- Avoid top-level side effects that import `PySide6`, `bw2data` or other heavy deps. Tests run faster when imports are delayed, and startup code purposely delays heavy imports.
- Database read/write state is managed via `ProjectSettings` and Brightway dataset hooks - be careful when mutating databases; use Brightway APIs and trigger appropriate signals when needed.
- UI tests rely on `pytest-qt`. When adding UI features, include a minimal non-blocking test where possible.

Files to reference when modifying behavior
- Startup & entry: `activity_browser/__main__.py`, `run-activity-browser.py`
- App class: `activity_browser/ui/application.py`
- Signals & bw2data integration: `activity_browser/signals.py`
- Settings: `activity_browser/settings.py`
- Layouts/pages/widgets: `activity_browser/layouts/` and `activity_browser/ui/widgets.py`
- Actions: `activity_browser/actions/` (see `base.py` for the pattern)

Safety and change scope guidance for AI edits
- Small, localized changes only: prefer edits to single files or small APIs. Large refactors require human review.
- When changing stateful behavior (settings, databases, signals), add or update tests and emit/observe the same signals existing code expects.
- Preserve delayed-import patterns. If you need to import heavy modules, add them inside functions or worker threads similar to `__main__.ModuleThread`.

Examples (concrete patterns to follow)
- Register a global shortcut:
  - Use @application.global_shortcut("Ctrl+S") above the function to register it and rely on `application.main_window` to attach the shortcut.
- Emit a UI update when a database is written:
  - Use `activity_browser.signals.signals.database.written.emit(Database(name))` or rely on bw2data to trigger the patched signals.
- Add a settings value:
  - Update `ABSettings.get_default_settings()` and access via `ab_settings.current_bw_dir` or `ab_settings.write_settings()`.

If anything in this file is unclear or you'd like more detail (examples for plugins, how signals are patched to bw2data, or test examples), tell me which area to expand and I'll update the instructions.
