# delegates

Qt item delegates for custom cell rendering and editing in tables and trees.

## Overview

This directory contains custom Qt delegates that control how data is displayed and edited in table and tree views throughout Activity Browser. Delegates enable specialized rendering, validation, and editing behavior for different data types.

## What are Delegates?

In Qt's Model/View architecture, delegates handle:
- **Display** - How data appears in cells (colors, icons, formatting)
- **Editing** - What widget appears when user edits a cell
- **Validation** - Checking user input before accepting
- **Decoration** - Adding icons, colors, or other visual elements

## Usage Pattern

Assign delegates to specific columns by defining them in the `defaultColumnDelegates` attribute of the `ABTreeView` class:

```python
class View(widgets.ABTreeView):
    """
    A view that displays the exchanges in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
        hovered_item (ExchangesItem): The item currently being hovered over.
    """
    defaultColumnDelegates = {
        "column_name": delegates.DelegateYouWantToUse,
    }
```


## Creating Custom Delegates

Inherit from `QStyledItemDelegate`:

```python
from qtpy.QtWidgets import QStyledItemDelegate, QLineEdit

class MyDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        """Create the editing widget."""
        editor = QLineEdit(parent)
        editor.setValidator(...)  # Add validation
        return editor
    
    def setEditorData(self, editor, index):
        """Load data into editor."""
        value = index.data(Qt.EditRole)
        editor.setText(str(value))
    
    def setModelData(self, editor, model, index):
        """Save editor data back to model."""
        value = editor.text()
        model.setData(index, value, Qt.EditRole)
    
    def displayText(self, value, locale):
        """Format value for display."""
        return f"{value:.2f}"
```

## Key Methods

### `createEditor(parent, option, index)`
Creates the widget used for editing:
- **parent** - Parent widget for the editor
- **option** - Style options for the item
- **index** - Model index being edited
- **Returns** - Editor widget (QLineEdit, QComboBox, etc.)

### `setEditorData(editor, index)`
Populates the editor with current value:
- **editor** - The editor widget
- **index** - Model index with data

### `setModelData(editor, model, index)`
Saves edited value back to model:
- **editor** - The editor widget
- **model** - The data model
- **index** - Model index to update

### `displayText(value, locale)`
Formats value for display (optional):
- **value** - Raw data value
- **locale** - Locale for formatting
- **Returns** - Formatted string

### `paint(painter, option, index)`
Custom rendering (advanced):
- **painter** - QPainter for drawing
- **option** - Style options
- **index** - Model index to render

## Validation

Add validators to editors:

```python
def createEditor(self, parent, option, index):
    editor = QLineEdit(parent)
    validator = QDoubleValidator(0.0, 1000.0, 2, editor)
    editor.setValidator(validator)
    return editor
```

## Signal Handling

Delegates can emit signals on edits:

```python
from qtpy.QtCore import Signal

class MyDelegate(QStyledItemDelegate):
    editingFinished = Signal(QModelIndex, object)
    
    def setModelData(self, editor, model, index):
        value = editor.text()
        model.setData(index, value)
        self.editingFinished.emit(index, value)
```

## Development Guidelines

When creating delegates:

1. **Inherit from QStyledItemDelegate** - Preferred over QItemDelegate
2. **Validate input** - Add QValidator to editors
3. **Handle edge cases** - Empty values, invalid data, cancellation
4. **Match data types** - Editor should match model data type
5. **Close editor properly** - Emit closeEditor signal when done
6. **Keep it simple** - Complex editing might need a dialog
7. **Test thoroughly** - Verify editing, validation, display
8. **Consider performance** - Efficient for many cells
9. **Support keyboard** - Tab, Enter, Escape navigation
10. **Provide feedback** - Visual cues for invalid input
