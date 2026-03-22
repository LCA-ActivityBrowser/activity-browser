# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets


class BaseSettingsChapter(QtWidgets.QWidget):
    """Base class for settings chapters."""
    
    # Signal emitted when settings change
    changed = QtCore.Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_page = parent
        self._initial_state = None
    
    def get_current_state(self):
        """
        Override this to return the current state of the chapter.
        Should return a dictionary or tuple representing current values.
        """
        return {}
    
    def has_changes(self):
        """Check if the chapter has unsaved changes."""
        if self._initial_state is None:
            return False
        return self.get_current_state() != self._initial_state
    
    def save_settings(self):
        """Override this to save chapter-specific settings."""
        pass
    
    def reset(self):
        """Override this to reset chapter to initial values."""
        pass
    
    def restore_defaults(self):
        """Override this to restore default values."""
        pass
