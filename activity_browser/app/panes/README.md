# panes

Dock-able side panels that can be arranged around the main content area.

## Overview

This directory contains pane widgets that can be docked to the edges of the main window or floated as separate windows. Panes provide quick access to navigation, information, and tools while working with the main content pages.

## Purpose

Panes offer:
- **Quick navigation** - Browse databases, activities, methods
- **Contextual information** - Show details about selected items
- **Tool access** - Quick access to common tools and operations
- **Workspace customization** - Users can arrange panes to suit their workflow

## Pane Architecture

Panes inherit from `AbstractPane` (in `ui/widgets/abstract_pane.py`) which provides:
- Dock widget functionality
- Consistent styling
- Signal connections
- State persistence (dock position, visibility)

## Existing Panes
- **Databases Pane** - View of available databases
- **Database Products Pane** - Search and browse product-type nodes within a database
- **Impact Categories Pane** - Browse impact assessment methods
- **Calculation Setups Pane** - List of Calculation Setups

## Pane Features

### Docking Behavior
Panes can be:
- Docked to window edges (left, right, top, bottom)
- Stacked with other panes (tabbed)
- Floated as separate windows
- Resized by dragging dividers
- Hidden/shown via View menu

### State Persistence
Pane positions and visibility are saved between sessions:
- Dock area and position
- Floating window geometry
- Visibility state
- Tab order when stacked

## Usage Pattern

```python
from activity_browser.ui.widgets import AbstractPane

class MyPane(AbstractPane):
    def __init__(self, parent=None):
        super().__init__(parent)
```

## Development Guidelines

When creating new panes:

- **Inherit from AbstractPane** - Use the base class for consistency
- **Set pane title** - Use the standard `PaneNamePane` naming convention to set the title automatically
- **Base panes** - Add base panes to `__init__.py` in this directory so they are loaded by the main window on project change.


## Visibility Control

Panes can be shown/hidden via:
- View menu (one menu item per pane)
- Toolbar buttons
- Keyboard shortcuts
- Context menu on title bar

The main window tracks pane visibility and provides a centralized way to manage them.
