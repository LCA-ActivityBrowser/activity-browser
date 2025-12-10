# wizards

Multi-step wizard dialogs for complex workflows.

## Overview

This directory contains wizard dialogs that guide users through multi-step processes such as database import, project setup, and configuration tasks. Wizards provide a structured approach to complex operations.

## What is a Wizard?

A wizard is a multi-page dialog that:
- Guides users step-by-step through a process
- Validates input at each step
- Allows forward/backward navigation
- Shows progress through the workflow
- Collects all necessary information before completion

## When to Use Wizards

Use wizards for:
- **Complex setup** - Initial configuration with many options
- **Multi-step workflows** - Processes requiring sequential steps
- **Data collection** - Gathering information in logical groups
- **Import/export** - File selection, options, mapping, preview
- **Guided operations** - Help users through unfamiliar tasks

Don't use wizards for:
- Simple forms (use a regular dialog)
- Single-step operations
- Expert users who know what they want
- When flexibility in order is needed

## Wizard Components

### Wizard Dialog
The main container (inherits from `QWizard`):
- Manages pages
- Handles navigation
- Provides standard buttons (Next, Back, Finish, Cancel)
- Tracks completion state

### Wizard Pages
Individual steps (inherit from `QWizardPage`):
- Collect specific information
- Validate input
- Determine if page is complete
- Navigate to next page

## Usage Pattern

### Creating a Wizard

```python
from qtpy.QtWidgets import QWizard

class MyWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Wizard")
        
        # Add pages
        self.addPage(IntroPage())
        self.addPage(ConfigPage())
        self.addPage(ConfirmPage())
        
    def accept(self):
        # Process collected data
        self.process_results()
        super().accept()
```

### Creating Wizard Pages

```python
from qtpy.QtWidgets import QWizardPage, QVBoxLayout, QLineEdit

class ConfigPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Configuration")
        self.setSubTitle("Enter configuration details")
        
        layout = QVBoxLayout(self)
        self.name_edit = QLineEdit()
        self.registerField("name*", self.name_edit)  # * = required
        layout.addWidget(self.name_edit)
        
    def validatePage(self):
        """Called when Next is clicked."""
        if not self.name_edit.text():
            return False
        return True
```

## Wizard Features

### Field Registration
Share data between pages:
```python
# In page 1
self.registerField("database_name*", self.name_edit)

# In page 2
db_name = self.field("database_name")
```

### Required Fields
Mark fields as required (asterisk):
```python
self.registerField("email*", self.email_edit)
```

Next button is disabled until all required fields are filled.

### Page Validation
Control when users can proceed:
```python
def validatePage(self):
    """Return False to prevent proceeding."""
    if not self.validate_input():
        QMessageBox.warning(self, "Error", "Invalid input")
        return False
    return True
```

### Conditional Navigation
Skip pages based on choices:
```python
def nextId(self):
    """Return ID of next page."""
    if self.skip_option.isChecked():
        return self.SummaryPage  # Skip intermediate pages
    return super().nextId()
```

### Dynamic Content
Update pages based on previous choices:
```python
def initializePage(self):
    """Called when page is shown."""
    selection = self.field("user_selection")
    self.update_options(selection)
```

## Wizard Buttons

### Standard Buttons
- **Next** - Proceed to next page (calls `validatePage()`)
- **Back** - Return to previous page
- **Finish** - Complete wizard (calls `accept()`)
- **Cancel** - Abort wizard (calls `reject()`)
- **Help** - Show help (optional, connect to help system)

### Customizing Buttons
```python
self.setButtonText(QWizard.NextButton, "Continue")
self.setButtonText(QWizard.FinishButton, "Import")
```

### Button Visibility
```python
self.button(QWizard.BackButton).setVisible(False)
```

## Wizard Styles

Choose wizard style:
```python
# Modern style (default)
wizard.setWizardStyle(QWizard.ModernStyle)

# Classic style with sidebar
wizard.setWizardStyle(QWizard.ClassicStyle)

# Mac style
wizard.setWizardStyle(QWizard.MacStyle)
```

## Page Types

### Intro Page
Welcome and overview:
```python
class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("This wizard will guide you..."))
```

### Input Page
Collect user input:
```python
class InputPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Enter Information")
        # Add input fields
```

### Selection Page
Choose options:
```python
class SelectionPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Select Options")
        # Add radio buttons or checkboxes
```

### Preview Page
Review before finishing:
```python
class PreviewPage(QWizardPage):
    def initializePage(self):
        # Show summary of all choices
        summary = self.generate_summary()
        self.label.setText(summary)
```

## Threading in Wizards

Long operations in `accept()`:
```python
def accept(self):
    # Show progress
    self.progress = QProgressDialog("Importing...", None, 0, 0, self)
    self.progress.show()
    
    # Run in background
    worker = ABThread(self.import_data)
    worker.finished.connect(self.on_complete)
    worker.start()

def on_complete(self):
    self.progress.close()
    super().accept()
```

## Development Guidelines

When creating wizards:

1. **Plan page flow** - Map out all steps before coding
2. **Keep pages focused** - One task per page
3. **Validate early** - Check input on each page
4. **Provide context** - Clear titles and subtitles
5. **Use fields wisely** - Register fields to share data
6. **Enable navigation** - Implement validatePage() properly
7. **Show progress** - Use page numbers or progress indicator
8. **Provide help** - Add help button with useful information
9. **Test all paths** - Verify all navigation possibilities
10. **Handle cancellation** - Clean up partial work

## Example: Import Wizard

```python
class ImportWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Database")
        
        self.file_page = FileSelectionPage()
        self.options_page = ImportOptionsPage()
        self.preview_page = PreviewPage()
        
        self.addPage(self.file_page)
        self.addPage(self.options_page)
        self.addPage(self.preview_page)
        
    def accept(self):
        filepath = self.field("filepath")
        options = self.get_options()
        self.perform_import(filepath, options)
        super().accept()
```

## Integration with Actions

Wizards are typically opened via actions:

```python
from activity_browser.app.actions.base import ABAction

class OpenImportWizard(ABAction):
    text = "Import Database..."
    
    @staticmethod
    def run():
        wizard = ImportWizard()
        if wizard.exec_() == QWizard.Accepted:
            # Import completed successfully
            pass
```
