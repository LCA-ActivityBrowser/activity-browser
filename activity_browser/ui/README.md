# ui

Core UI components and widgets for the Activity Browser interface.

## Overview

This module contains reusable UI components, custom widgets, dialog windows, wizards, and web views that make up the Activity Browser user interface. These components are built using Qt (PySide6) via the qtpy compatibility layer.

## Directory Structure

- **`core/`** - Core UI classes including the application class, threading, and tree models
- **`delegates/`** - Qt item delegates for custom cell rendering in tables and trees
- **`dialogs/`** - Dialog windows for various user interactions
- **`web/`** - Web views for HTML-based visualizations
- **`widgets/`** - Reusable custom widget components
- **`wizards/`** - Multi-step wizard dialogs

## Key Files

- **`icons.py`** - Icon loading and management utilities

## Core Components

### `core/`
- **`application.py`** - `ABApplication` class extending QApplication with global shortcuts
- **`threading.py`** - Worker threads for background operations
- **`tree_model.py`** - Custom tree models for hierarchical data
- **`mimedata.py`** - Custom MIME data for drag-and-drop operations

### `widgets/`
Custom reusable widgets:
- **`abstract_page.py`** - Base class for main content pages
- **`abstract_pane.py`** - Base class for dock panes
- **`buttons.py`** - Custom button widgets
- **`combobox.py`** - Enhanced combo box widgets
- **`tree_view.py`** - Custom tree view components
- **`table_view.py`** - Custom table view components
- **`plot.py`** - Plotting widgets
- And many more specialized widgets...

## Design Patterns

### Abstract Base Classes
Many widgets inherit from abstract base classes:
- `AbstractPage` - For main content area pages
- `AbstractPane` - For dock-able side panels

### Custom Widgets
Widgets extend Qt base classes to add:
- Custom styling and appearance
- Application-specific behavior
- Signal/slot connections
- Validation and error handling

### Delegates
Item delegates customize table/tree cell rendering and editing:
- Custom editors for specific data types
- Validation during inline editing
- Formatted display of values

## Qt Integration

All UI components use **qtpy** for Qt compatibility:

```python
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt, Signal, Slot
```

This allows flexibility in Qt bindings (PySide6, PyQt6, etc.).

## Usage Pattern

Import widgets as needed:

```python
from activity_browser.ui.widgets import AbstractPage
from activity_browser.ui.core.application import ABApplication
from activity_browser.ui.dialogs import MyDialog
```

## Development Guidelines

- Inherit from abstract base classes when appropriate
- Use qtpy imports for Qt compatibility
- Connect to global signals for cross-component communication
- Keep widgets reusable and decoupled from application logic
- Follow Qt naming conventions (camelCase for methods)
- Emit signals for state changes rather than direct calls
