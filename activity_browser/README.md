# activity_browser

This is the main package directory for the Activity Browser application.

## Overview

Activity Browser is a Qt-based desktop application that provides a GUI front-end for Brightway2, enabling users to perform Life Cycle Assessment (LCA) calculations with an intuitive interface.

## Directory Structure

- **`app/`** - Main application logic, including the main window, actions, dialogs, pages, and panes
- **`bwutils/`** - Utility functions and helpers that extend Brightway2 functionality
- **`mod/`** - Monkey-patches and modifications to third-party libraries (bw2analyzer, bw2io, etc.)
- **`static/`** - Static resources including HTML templates, CSS, icons, fonts, and JavaScript files
- **`ui/`** - Core UI components including widgets, dialogs, wizards, and web views

## Key Files

- **`__init__.py`** - Package initialization with PySide6/typing compatibility patches
- **`__main__.py`** - Entry point for the application (`run_activity_browser` function)
- **`info.py`** - Version and application metadata

## Entry Points

The application can be started in multiple ways:
- Console script: `activity-browser` (installed via setuptools)
- Direct module execution: `python -m activity_browser`
- Script execution: `python run-activity-browser.py`

All entry points lead to `activity_browser.__main__:run_activity_browser`.

## Architecture

The application follows an MVC-like pattern with:
- **Global signals** (`activity_browser.app.signals`) - Event bus for cross-component communication
- **Deferred imports** - Heavy modules are loaded in background threads during startup
- **Actions pattern** - UI operations encapsulated in `app/actions/` with a base class pattern

## Dependencies

Main dependencies include:
- **PySide6** (via qtpy) - Qt bindings for the GUI
- **Brightway2** ecosystem (bw2data, bw2calc, bw2analyzer, bw2io) - LCA calculation engine
- **loguru** - Logging framework

## Development Notes

- Avoid top-level imports of heavy modules (PySide6, bw2data) to keep tests fast
- Use project signals for cross-component communication instead of direct function calls
- Global shortcuts are registered via `@application.global_shortcut` decorator
