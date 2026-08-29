# Settings Module

This module contains the settings page and its chapters.

## Structure

```
settings/
├── __init__.py          # Module exports; registers base chapters on import
├── settings_page.py     # Main SettingsPage class
├── base.py              # BaseSettingsChapter (base class for all chapters)
├── base_chapters.py     # BASE_SETTINGS_CHAPTERS registry (like pages.base_pages)
├── startup.py           # StartupSettingsChapter
├── appearance.py        # AppearanceSettingsChapter
├── project_manager.py   # ProjectManagerSettingsChapter
├── metadatastore.py     # MetadataStoreSettingsChapter
├── plugins.py           # PluginsSettingsChapter
└── README.md            # This file
```

## Adding a New Base Chapter

Base chapters ship with Activity Browser. Plugin chapters register via
`PluginContext.register_settings_chapter` instead.

### Step 1: Create a new chapter file

Create a new file in this directory, e.g., `my_chapter.py`:

```python
# -*- coding: utf-8 -*-
from loguru import logger
from qtpy import QtWidgets

from activity_browser.app import settings
from .base import BaseSettingsChapter


class MySettingsChapter(BaseSettingsChapter):
    """Chapter for my settings."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.my_widget = QtWidgets.QLineEdit()

        self.build_layout()
        self.connect_signals()
        self.reset()

    def connect_signals(self):
        self.my_widget.textChanged.connect(self.changed.emit)

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()

        group = QtWidgets.QGroupBox("My Settings")
        group_layout = QtWidgets.QGridLayout()
        group_layout.addWidget(QtWidgets.QLabel("Setting:"), 0, 0)
        group_layout.addWidget(self.my_widget, 0, 1)
        group.setLayout(group_layout)

        layout.addWidget(group)
        layout.addStretch()

        self.setLayout(layout)

    def get_current_state(self):
        return {"my_setting": self.my_widget.text()}

    def set_settings(self):
        settings.global_config.setdefault("my_setting", self.my_widget.text())

    def reset(self):
        value = settings.global_config.get("my_setting", "")
        self.my_widget.setText(value)
        self._initial_state = self.get_current_state()
```

### Step 2: Register in `base_chapters.py`

Add your chapter to `BASE_SETTINGS_CHAPTERS` (sidebar order):

```python
from .my_chapter import MySettingsChapter

BASE_SETTINGS_CHAPTERS: Tuple[Tuple[str, Type], ...] = (
    # ...
    ("My Chapter", MySettingsChapter),
)
```

`SettingsPage` builds its sidebar from `contributions.settings_chapters`, which
base chapters populate via `register_base_settings_chapters()` in `__init__.py`.

That's it — no changes to `settings_page.py` are required.

## BaseSettingsChapter Interface

All chapters must inherit from `BaseSettingsChapter` and implement these methods:

- **`get_current_state()`** - Return the current state as a dictionary for change tracking
- **`set_settings()`** - Save the chapter's settings (called when the user clicks Save)
- **`reset()`** - Reset widgets to the last saved state
- **`has_changes()`** - Provided by the base class when `get_current_state()` is implemented

### Change Tracking

The base class automatically tracks changes using the `changed` signal:

1. Override `get_current_state()` to return a dictionary of current values
2. Connect widget signals to `self.changed.emit()` to notify of changes
3. The save button will be enabled/disabled automatically based on changes

Example:

```python
def connect_signals(self):
    self.my_widget.textChanged.connect(self.changed.emit)

def get_current_state(self):
    return {"my_value": self.my_widget.text()}
```

## Existing Chapters

### StartupSettingsChapter (`startup.py`)
Manages:
- Brightway directory selection and management
- Startup project selection
- Shown pages and panes at startup
- Directory validation and project discovery

### AppearanceSettingsChapter (`appearance.py`)
Manages:
- Theme selection (Light/Dark)
- Pane tab position and plot palette

### ProjectManagerSettingsChapter (`project_manager.py`)
Manages:
- Project management settings
- Project creation and deletion

### MetadataStoreSettingsChapter (`metadatastore.py`)
Manages:
- Metadata store caching settings
- Searcher configuration

### PluginsSettingsChapter (`plugins.py`)
Manages:
- Discovered plugins (entry points)
- Global enable/disable (save and restart to apply)

## Best Practices

1. **Keep chapters focused** - Each chapter should handle a specific area of settings
2. **Use QGroupBox** - Organize widgets within chapters using group boxes
3. **Add tooltips** - Help users understand what each setting does
4. **Validate input** - Check settings before saving
5. **Log changes** - Use logger to record setting changes
6. **Handle errors gracefully** - Show appropriate error messages to users
