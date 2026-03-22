# core

Core UI classes and utilities for the Activity Browser interface.

## Overview

This directory contains fundamental UI classes that provide the foundation for Activity Browser's user interface, including the main application class, threading utilities, tree models, and MIME data handling.

## Key Files

### `application.py`
**ABApplication** - Main Qt application class

Extends `QApplication` with Activity Browser-specific functionality:
- **Global shortcuts** - Register keyboard shortcuts across the application
- **Main window reference** - Centralized access to main window
- **Application lifecycle** - Startup, shutdown, event handling
- **Style management** - Application-wide styling and theming

```python
from activity_browser.ui.core.application import ABApplication

app = ABApplication()
app.main_window = main_window

@app.global_shortcut("Ctrl+S")
def save_action():
    # Triggered by Ctrl+S anywhere in the app
    pass
```

### `threading.py`
**ABThread** - Worker thread for background operations

Provides threading utilities to keep the UI responsive:
- Run long operations in background
- Progress reporting
- Thread-safe signal emission
- Cancellation support

```python
from activity_browser.ui.core.threading import ABThread

def long_operation(progress_callback):
    for i in range(100):
        # Do work
        progress_callback(i)
        
worker = ABThread(long_operation)
worker.progress.connect(update_progress_bar)
worker.finished.connect(on_complete)
worker.start()
```

### `tree_model.py`
Custom tree models for hierarchical data display

Implements Qt's model/view architecture for tree structures:
- **Efficient data handling** - Lazy loading of tree nodes
- **Custom data roles** - Additional data beyond display
- **Drag and drop** - Support for tree item manipulation
- **Filtering and sorting** - Built-in data organization

```python
from activity_browser.ui.core.tree_model import TreeModel

model = TreeModel(root_data)
tree_view.setModel(model)
```

### `mimedata.py`
Custom MIME data for drag-and-drop operations

Defines MIME types for Activity Browser data:
- Activities
- Exchanges
- Databases
- Methods
- Parameters

Enables drag-and-drop between different parts of the UI:

```python
from activity_browser.ui.core.mimedata import ActivityMimeData

# Create MIME data
mime = ActivityMimeData(activity_key)

# Set on drag operation
drag = QDrag(widget)
drag.setMimeData(mime)
```

## Architecture Patterns

### Application Singleton
`ABApplication` is a singleton accessed throughout the app:
```python
from activity_browser import app

app.application  # The ABApplication instance
```

### Threading Pattern
Long operations follow this pattern:
1. Create worker thread with target function
2. Connect signals (progress, finished, error)
3. Start thread (non-blocking)
4. Update UI via signals when complete

### Model/View Pattern
Tree and table data uses Qt's model/view:
- **Model** - Data management and business logic
- **View** - Data display and user interaction
- **Delegate** - Custom cell rendering and editing

## Global Shortcuts

Register shortcuts using the decorator:
```python
@app.application.global_shortcut("Ctrl+F")
def find_action():
    # Search dialog or functionality
    pass
```

Shortcuts are automatically attached when `app.main_window` is set.

## Development Guidelines

### Threading
- **Never block the main thread** - Use ABThread for slow operations
- **Update UI from main thread only** - Use signals to communicate back
- **Handle errors gracefully** - Catch exceptions in worker threads
- **Support cancellation** - Allow users to abort long operations

### Models
- **Lazy loading** - Load data only when needed
- **Efficient updates** - Use beginInsertRows/endInsertRows properly
- **Custom roles** - Define additional data roles for internal use
- **Sort/filter proxies** - Use QSortFilterProxyModel for filtering

### MIME Data
- **Use specific MIME types** - Define clear types for each data kind
- **Include sufficient data** - Store enough info for the drop target
- **Check compatibility** - Validate MIME data before accepting drops

## Performance Considerations

### Tree Models
- Implement lazy loading for large trees
- Cache frequently accessed data
- Use flat data structures when possible
- Batch updates with begin/end calls

### Threading
- Pool threads for multiple small operations
- Cancel obsolete operations when new ones start
- Clean up thread resources properly
- Monitor thread count to avoid resource exhaustion

## Signal/Slot Connections

Core classes emit important signals:

**ABThread**:
- `started` - Thread began execution
- `progress(int)` - Progress update (0-100)
- `finished` - Thread completed successfully
- `error(Exception)` - Thread encountered an error

**TreeModel**:
- `dataChanged` - Model data was modified
- `rowsInserted` - New rows added
- `rowsRemoved` - Rows deleted
- `modelReset` - Model structure changed completely

Connect to these signals to keep UI synchronized with data changes.
