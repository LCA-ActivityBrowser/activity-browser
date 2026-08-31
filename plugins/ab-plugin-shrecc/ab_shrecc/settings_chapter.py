# -*- coding: utf-8 -*-
"""SHRECC plugin Settings chapter."""
from activity_browser.plugins import BaseSettingsChapter
from qtpy import QtWidgets


class ShreccSettingsChapter(BaseSettingsChapter):
    def __init__(self, parent=None, *, plugin_settings=None):
        super().__init__(parent)
        self._plugin_settings = plugin_settings
        self.data_dir = QtWidgets.QLineEdit()
        self.data_dir.setPlaceholderText("SHRECC data directory (optional)")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("SHRECC plugin preferences"))
        layout.addWidget(QtWidgets.QLabel("Data directory"))
        layout.addWidget(self.data_dir)
        layout.addStretch()
        self.data_dir.textChanged.connect(lambda: self.changed.emit())
        self.reset()

    def get_current_state(self):
        return {"data_dir": self.data_dir.text()}

    def reset(self):
        data = self._plugin_settings
        text = ""
        if data is not None:
            text = data.get("data_dir", text)
        self.data_dir.setText(text)
        self._initial_state = self.get_current_state()

    def set_settings(self):
        data = self._plugin_settings
        if data is not None:
            data["data_dir"] = self.data_dir.text()
