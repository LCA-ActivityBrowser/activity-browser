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
        "dark": "Dark theme",
    }
    
    pane_tab_position_map = {
        "top": "Top",
        "bottom": "Bottom",
        "left": "Left",
        "right": "Right",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Theme selector
        self.theme_combo = QtWidgets.QComboBox()
        
        # Pane tab position selector
        self.pane_tab_position_combo = QtWidgets.QComboBox()
        
        self.build_layout()
        self.connect_signals()
        self.reset()
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Emit changed signal when settings change
        self.theme_combo.currentTextChanged.connect(lambda: self.changed.emit())
        self.pane_tab_position_combo.currentTextChanged.connect(lambda: self.changed.emit())
    
    def build_layout(self):
        """Build the chapter layout."""
        layout = QtWidgets.QVBoxLayout()
        
        # Theme section
        theme_group = QtWidgets.QGroupBox("Theme")
        theme_layout = QtWidgets.QGridLayout()
        theme_layout.addWidget(QtWidgets.QLabel("Theme:"), 0, 0)
        theme_layout.addWidget(self.theme_combo, 0, 1)
        theme_group.setLayout(theme_layout)
        
        # Pane tab position section
        pane_tab_group = QtWidgets.QGroupBox("Pane Tab Position")
        pane_tab_layout = QtWidgets.QGridLayout()
        pane_tab_layout.addWidget(QtWidgets.QLabel("Position:"), 0, 0)
        pane_tab_layout.addWidget(self.pane_tab_position_combo, 0, 1)
        pane_tab_group.setLayout(pane_tab_layout)
        
        layout.addWidget(theme_group)
        layout.addWidget(pane_tab_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    # --- Settings management methods --- #
    def reset(self):
        """(Re)set to initial values."""
        self.theme_combo.clear()
        self.theme_combo.addItems(self.theme_map.values())
        self.theme_combo.setCurrentText(self.theme_map.get(settings["appearance"]["theme"], "System default"))
        
        self.pane_tab_position_combo.clear()
        self.pane_tab_position_combo.addItems(self.pane_tab_position_map.values())
        self.pane_tab_position_combo.setCurrentText(self.pane_tab_position_map.get(settings["appearance"]["pane_tab_position"], "Bottom"))

    def has_changes(self):
        """Check if there are unsaved changes."""
        current_state = {
            'theme': self.theme_combo.currentText(),
            'pane_tab_position': self.pane_tab_position_combo.currentText(),
        }
        initial_state = {
            'theme': self.theme_map.get(settings["appearance"]["theme"], "System default"),
            'pane_tab_position': self.pane_tab_position_map.get(settings["appearance"]["pane_tab_position"], "Bottom"),
        }
        return current_state != initial_state
    
    def set_settings(self):
        """Save appearance settings."""
        new_theme = self.theme_combo.currentText()
        settings["appearance"]["theme"] = [key for key, value in self.theme_map.items() if value == new_theme][0]
        
        new_pane_position = self.pane_tab_position_combo.currentText()
        settings["appearance"]["pane_tab_position"] = [key for key, value in self.pane_tab_position_map.items() if value == new_pane_position][0]

