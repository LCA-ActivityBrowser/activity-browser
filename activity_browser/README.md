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

## Development Notes

- See `CONTRIBUTING.md` for guidelines on contributing to the project
- Check out the Development notes specific to each submodule for more details on implementation
