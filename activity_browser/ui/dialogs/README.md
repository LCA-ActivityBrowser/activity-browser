# dialogs

UI dialog windows for various user interactions.

## Overview

This directory contains dialog windows used throughout Activity Browser for user interactions such as configuration, data entry, item selection, and information display.

## Dialog Categories

### Input Dialogs
Collect information from users:
- Text input dialogs
- Numeric value entry
- Form-based data entry
- Multi-field configuration

### Selection Dialogs
Allow users to choose items:
- Activity selection
- Database selection
- Method selection
- File/directory choosers
- List item selection

### Configuration Dialogs
Manage settings and preferences:
- Application settings
- Project settings
- Database properties
- Import/export configuration
- Plugin configuration

### Information Dialogs
Display information to users:
- About dialog
- Progress dialogs
- Status messages
- Error and warning dialogs
- Help and documentation

### Confirmation Dialogs
Request user confirmation:
- Delete confirmations
- Overwrite warnings
- Action confirmations
- Discard changes prompts

## Common Dialog Types

### QDialog-based
Standard modal dialogs:
```python
from qtpy.QtWidgets import QDialog

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def accept(self):
        if self.validate():
            # Process and close
            super().accept()
```

### QMessageBox-based
Simple message dialogs:
```python
from qtpy.QtWidgets import QMessageBox

result = QMessageBox.question(
    parent,
    "Confirm Delete",
    "Are you sure you want to delete this item?",
    QMessageBox.Yes | QMessageBox.No
)
```

### QFileDialog-based
File and directory selection:
```python
from qtpy.QtWidgets import QFileDialog

filepath = QFileDialog.getOpenFileName(
    parent,
    "Select File",
    "",
    "Excel files (*.xlsx)"
)
```

## Dialog Features

### Modal vs. Modeless
- **Modal** - Blocks parent window until closed (most common)
- **Modeless** - Allows interaction with parent (for utilities)

### Button Boxes
Standard button configurations:
```python
from qtpy.QtWidgets import QDialogButtonBox

buttons = QDialogButtonBox(
    QDialogButtonBox.Ok | QDialogButtonBox.Cancel
)
buttons.accepted.connect(self.accept)
buttons.rejected.connect(self.reject)
```

### Validation
Validate before accepting:
```python
def accept(self):
    if not self.name_input.text():
        QMessageBox.warning(self, "Error", "Name is required")
        return
    super().accept()
```

### Progress Indication
Show progress for long operations:
```python
from qtpy.QtWidgets import QProgressDialog

progress = QProgressDialog("Processing...", "Cancel", 0, 100, parent)
progress.setWindowModality(Qt.WindowModal)
progress.setValue(50)
```

## Usage Patterns

### Simple Confirmation
```python
from qtpy.QtWidgets import QMessageBox

reply = QMessageBox.question(
    self,
    "Confirm",
    "Delete this database?",
    QMessageBox.Yes | QMessageBox.No,
    QMessageBox.No  # Default button
)

if reply == QMessageBox.Yes:
    # Perform deletion
    pass
```

### Custom Dialog
```python
class MyDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add widgets
        self.name_edit = QLineEdit()
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_result(self):
        """Return dialog result."""
        return self.name_edit.text()
```

### Using Custom Dialog
```python
dialog = MyDialog(data, parent=self)
if dialog.exec_() == QDialog.Accepted:
    result = dialog.get_result()
    # Use result
```

## Development Guidelines

When creating dialogs:

1. **Inherit from QDialog** - Use Qt's base dialog class
2. **Set parent** - Pass parent widget for proper hierarchy
3. **Provide clear title** - Set window title with setWindowTitle()
4. **Use button boxes** - Standard OK/Cancel buttons
5. **Validate input** - Check data in accept() method
6. **Return results** - Provide method to get dialog results
7. **Handle cancellation** - Clean up if user cancels
8. **Size appropriately** - Fit content, but not too large
9. **Be modal when needed** - Block parent for critical choices
10. **Show progress** - Use QProgressDialog for long operations

## Threading in Dialogs

Long operations should use worker threads:

```python
from activity_browser.ui.core.threading import ABThread

class MyDialog(QDialog):
    def accept(self):
        # Show progress
        self.progress = QProgressDialog("Processing...", None, 0, 0, self)
        self.progress.show()
        
        # Run in background
        worker = ABThread(self.process_data)
        worker.finished.connect(self.on_complete)
        worker.start()
    
    def on_complete(self):
        self.progress.close()
        super().accept()
```

## Signal Integration

Dialogs should emit signals for application updates:

```python
from activity_browser import app

class MyDialog(QDialog):
    def accept(self):
        # Save data
        self.save_changes()
        
        # Notify application
        app.signals.data_changed.emit()
        
        super().accept()
```

## Accessibility

Make dialogs accessible:
- Clear focus order (tab navigation)
- Keyboard shortcuts for buttons
- Screen reader compatible labels
- Escape key to cancel
- Enter key to accept (when safe)

## Testing

Test dialogs thoroughly:
```python
def test_my_dialog(qtbot):
    dialog = MyDialog()
    qtbot.addWidget(dialog)
    
    # Test initial state
    assert dialog.name_edit.text() == ""
    
    # Simulate user input
    qtbot.keyClicks(dialog.name_edit, "Test Name")
    
    # Test validation
    dialog.accept()
    assert dialog.result() == QDialog.Accepted
```
