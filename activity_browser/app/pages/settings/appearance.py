# -*- coding: utf-8 -*-
from loguru import logger
from qtpy import QtWidgets

from activity_browser.app import settings
from activity_browser.app.pages.settings.base import BaseSettingsChapter


class AppearanceSettingsChapter(BaseSettingsChapter):
    """Chapter for appearance-related settings."""

    theme_map = {
        "default": "System default",
        "light": "Light theme",
        "dark": "Dark theme compatibility",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Theme selector
        self.theme_combo = QtWidgets.QComboBox()
        
        self.build_layout()
        self.connect_signals()
        self.reset()
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Emit changed signal when settings change
        self.theme_combo.currentTextChanged.connect(lambda: self.changed.emit())
    
    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()
        
        # Theme section
        theme_group = QtWidgets.QGroupBox("Theme")
        theme_layout = QtWidgets.QGridLayout()
        theme_layout.addWidget(QtWidgets.QLabel("Theme:"), 0, 0)
        theme_layout.addWidget(self.theme_combo, 0, 1)
        theme_layout.addWidget(QtWidgets.QLabel("(Requires restart)"), 0, 2)
        theme_group.setLayout(theme_layout)
        
        layout.addWidget(theme_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    # --- Settings management methods --- #
    def reset(self):
        """(Re)set to initial values."""
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_map.values())
        self.theme_combo.setCurrentText(self.theme_map.get(settings["appearance"]["theme"], "System default"))

    def has_changes(self):
        """Check if there are unsaved changes."""
        current_state = {
            'theme': self.theme_combo.currentText(),
        }
        initial_state = {
            'theme': self.theme_map.get(settings["appearance"]["theme"], "System default"),
        }
        return current_state != initial_state
    
    def set_settings(self):
        """Save startup settings."""
        new_theme = self.theme_combo.currentText()
        settings["appearance"]["theme"] = [key for key, value in self.theme_map.items() if value == new_theme][0]

