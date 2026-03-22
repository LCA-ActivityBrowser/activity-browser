# app

Main application module containing the core logic and structure of the Activity Browser.

## Overview

This module orchestrates the main application components including the main window, menu bar, signal handling, and various UI elements organized into actions, dialogs, pages, and panes.

## Directory Structure

- **`actions/`** - Encapsulated UI operations and commands (activity, database, calculation setup, etc.)
- **`dialogs/`** - Dialog windows for user interactions
- **`pages/`** - Main content pages displayed in the application (activity details, calculations, parameters, etc.)
- **`panes/`** - Dock-able panes that can be arranged around the main content area

## Key Files

- **`__init__.py`** - Module initialization creating singleton instances:
  - `application` - ABApplication instance
  - `metadata` - MetaDataStore instance  
  - `settings` - Settings instance
  - `signals` - ABSignals instance (event bus)
  - `main_window` - MainWindow instance

- **`main_window.py`** - MainWindow class that holds the central widget and dock panes
- **`menu_bar.py`** - Application menu bar with File, Edit, View, Tools, Help menus
- **`signalling.py`** - ABSignals class that bridges bw2data signals to Qt signals

## Architecture

The app module creates and wires together the core application components:

1. **Application** (`ABApplication`) - Qt application instance with global shortcut management
2. **Signals** (`ABSignals`) - Project-wide event bus for model to UI communication
3. **Main Window** (`MainWindow`) - Main application window with pages and panes
4. **Actions** - Command pattern implementation for menu items and toolbar actions. Modifying Brightway2 happens here.
5. **Pages** - Content area widgets for different application views
6. **Panes** - Dock-able side panels

## Signal Flow

The signals instance serves as the central event bus:
- Bridges Brightway2 data events to Qt signals
- Enables loose coupling between UI components
- Used throughout the application for state updates

## Usage Pattern

Components should access the application objects via:

```python
from activity_browser import app

# Access global instances
app.application  # ABApplication instance
app.signals      # Event bus
app.settings     # Settings manager
app.metadata     # Metadata store
app.main_window  # Main window
```

## Development Notes

- See `CONTRIBUTING.md` for guidelines on contributing to the project
- This module is the place to add components that depend on the application having been initialized (e.g., actions, panes)
  - If the logic you want to add can only depend on brightway2, consider placing it in the `bwutils` submodule instead
  - If the widget you want to add does not depend on the application, consider placing it in the `ui` submodule instead
