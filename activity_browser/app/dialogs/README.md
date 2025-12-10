# dialogs

Dialog windows for user interactions throughout Activity Browser.

## Overview

This directory contains modal and non-modal dialog windows used for various user interactions such as data entry, configuration, selection, and information display.

## Purpose

Dialogs provide focused interfaces for:
- User input and data entry
- Configuration and settings
- Selection of items (activities, methods, databases)
- Information display and confirmations
- Multi-step workflows (see also `ui/wizards/`)

## Common Dialog Types

### Input Dialogs
- Text input fields
- Numeric value entry
- Date/time selection
- Multi-line text editing

### Selection Dialogs
- List/tree item selection
- Database/activity pickers
- Method selection
- File/directory choosers

### Configuration Dialogs
- Settings editors
- Preference panels
- Option configuration

### Information Dialogs
- Progress indicators
- Status messages
- Warnings and errors
- About/help information

## Design Guidelines

Dialogs in Activity Browser should:

1. **Be modal when appropriate** - Block parent window for critical decisions
2. **Provide clear actions** - OK/Cancel, Accept/Reject, or custom actions
3. **Validate input** - Check data before accepting
4. **Give feedback** - Show errors, warnings, progress
5. **Be responsive** - Use threading for long operations
6. **Follow Qt conventions** - Inherit from QDialog, use standard buttons

## Usage Pattern

```python
from qtpy.QtWidgets import QDialog, QDialogButtonBox

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Build dialog UI
        pass
        
    def accept(self):
        # Validate and process input
        if self.validate():
            super().accept()
```

## Integration with Actions

Dialogs are typically opened via actions:

```python
from activity_browser.app.actions.base import ABAction

class OpenMyDialog(ABAction):
    @staticmethod
    def run():
        dialog = MyDialog()
        if dialog.exec_() == QDialog.Accepted:
            # Process result
            pass
```

## Threading Considerations

Long-running operations in dialogs should use worker threads:

```python
from activity_browser.ui.core.threading import ABThread

class MyDialog(QDialog):
    def perform_long_operation(self):
        worker = ABThread(self.expensive_task)
        worker.finished.connect(self.on_complete)
        worker.start()
```

## Signal Emission

Dialogs should emit signals to notify the application of changes:

```python
from activity_browser import app

class MyDialog(QDialog):
    def accept(self):
        # Save changes
        self.save_data()
        # Notify application
        app.signals.data_changed.emit()
        super().accept()
```

This ensures the rest of the application can react to changes made in dialogs without tight coupling.
