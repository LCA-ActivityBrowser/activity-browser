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

## Common Pane Types

### Navigation Panes
- **Database browser** - Tree view of available databases
- **Activity browser** - Search and browse activities
- **Method browser** - Browse impact assessment methods
- **Project browser** - List of Brightway projects

### Information Panes
- **Details panel** - Show details of selected items
- **Properties** - Display item properties and metadata
- **History** - Recent actions or visited items

### Tool Panes
- **Quick calculations** - Run simple calculations
- **Search** - Global search interface
- **Console** - Python console for advanced users

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
        self.setup_ui()
        
    def setup_ui(self):
        # Build pane content
        pass
```

## Integration with Main Window

Panes are added to the main window as dock widgets:

```python
from activity_browser import app

pane = MyPane()
app.main_window.addDockWidget(Qt.LeftDockWidgetArea, pane)
```

## Signal Communication

Panes communicate with other components via signals:

```python
from activity_browser import app

class MyPane(AbstractPane):
    def on_item_selected(self, item):
        # Emit signal for other components
        app.signals.item_selected.emit(item)
```

## Development Guidelines

When creating new panes:

1. **Inherit from AbstractPane** - Use the base class for consistency
2. **Set pane title** - Provide a clear, descriptive title
3. **Keep focused** - Each pane should have a single, clear purpose
4. **Connect signals** - Listen for and emit relevant signals
5. **Handle updates** - Refresh when underlying data changes
6. **Support search/filter** - Allow users to find items quickly
7. **Provide context menus** - Right-click actions for items
8. **Make it closeable** - Users should be able to hide panes
9. **Support keyboard navigation** - Enable keyboard shortcuts

## Visibility Control

Panes can be shown/hidden via:
- View menu (one menu item per pane)
- Toolbar buttons
- Keyboard shortcuts
- Context menu on title bar

The main window tracks pane visibility and provides a centralized way to manage them.
