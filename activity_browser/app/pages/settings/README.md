# Settings Module

This module contains the settings page and its chapters.

## Structure

```
settings/
├── __init__.py          # Module exports
├── settings_page.py     # Main SettingsPage class
├── base.py              # BaseSettingsChapter (base class for all chapters)
├── startup.py           # StartupSettingsChapter
├── appearance.py        # AppearanceSettingsChapter
└── README.md            # This file
```

## Adding a New Chapter

### Step 1: Create a new chapter file

Create a new file in this directory, e.g., `my_chapter.py`:

```python
# -*- coding: utf-8 -*-
from loguru import logger
from qtpy import QtWidgets

from activity_browser.settings import ab_settings
from .base import BaseSettingsChapter


class MySettingsChapter(BaseSettingsChapter):
    """Chapter for my settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create your widgets
        self.my_widget = QtWidgets.QLineEdit()
        
        self.build_layout()
        self.connect_signals()
    
    def connect_signals(self):
        """Connect signals for change tracking."""
        self.my_widget.textChanged.connect(self.changed.emit)
    
    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()
        
        # Create your UI
        group = QtWidgets.QGroupBox("My Settings")
        group_layout = QtWidgets.QGridLayout()
        group_layout.addWidget(QtWidgets.QLabel("Setting:"), 0, 0)
        group_layout.addWidget(self.my_widget, 0, 1)
        group.setLayout(group_layout)
        
        layout.addWidget(group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def get_current_state(self):
        """Return current state for change tracking."""
        return {
            'my_setting': self.my_widget.text(),
        }
    
    def save_settings(self):
        """Save chapter-specific settings."""
        ab_settings.my_setting = self.my_widget.text()
        logger.info("Saved my settings")
    
    def reset(self):
        """Reset chapter to initial values."""
        self.my_widget.setText(ab_settings.my_setting)
    
    def restore_defaults(self):
        """Restore default values."""
        self.my_widget.setText("default value")
```

### Step 2: Import in settings_page.py

In `settings_page.py`, add your import:

```python
from .my_chapter import MySettingsChapter
```

### Step 3: Add to chapters list

In the `SettingsPage.__init__()` method, add your chapter:

```python
# Create chapters
self.startup_chapter = StartupSettingsChapter(self)
self.appearance_chapter = AppearanceSettingsChapter(self)
self.my_chapter = MySettingsChapter(self)  # <-- Add this

# Add chapters to the stack
self.chapters = [
    ("Startup", self.startup_chapter),
    ("Appearance", self.appearance_chapter),
    ("My Chapter", self.my_chapter),  # <-- And this
]
```

That's it! Your new chapter is now integrated.

## BaseSettingsChapter Interface

All chapters must inherit from `BaseSettingsChapter` and implement these methods:

- **`get_current_state()`** - Return the current state as a dictionary for change tracking
- **`save_settings()`** - Save the chapter's settings to `ab_settings`
- **`reset()`** - Reset widgets to current `ab_settings` values
- **`restore_defaults()`** - Set widgets to default values

### Change Tracking

The base class automatically tracks changes using the `changed` signal:

1. Override `get_current_state()` to return a dictionary of current values
2. Connect widget signals to `self.changed.emit()` to notify of changes
3. The save button will be enabled/disabled automatically based on changes

Example:
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.my_widget = QtWidgets.QLineEdit()
    self.build_layout()
    self.connect_signals()

def connect_signals(self):
    # Emit changed signal when the widget changes
    self.my_widget.textChanged.connect(self.changed.emit)

def get_current_state(self):
    """Return current state for change tracking."""
    return {
        'my_value': self.my_widget.text(),
    }
```

## Existing Chapters

### StartupSettingsChapter (`startup.py`)
Manages:
- Brightway directory selection and management
- Startup project selection
- Directory validation and project discovery

### AppearanceSettingsChapter (`appearance.py`)
Manages:
- Theme selection (Light/Dark)
- Future: Font sizes, colors, etc.

## Testing

Test the settings page with:

```bash
python test_settings_page.py
```

## Best Practices

1. **Keep chapters focused** - Each chapter should handle a specific area of settings
2. **Use QGroupBox** - Organize widgets within chapters using group boxes
3. **Add tooltips** - Help users understand what each setting does
4. **Validate input** - Check settings before saving
5. **Log changes** - Use logger to record setting changes
6. **Handle errors gracefully** - Show appropriate error messages to users
