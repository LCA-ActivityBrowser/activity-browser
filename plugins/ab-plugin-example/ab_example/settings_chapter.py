# -*- coding: utf-8 -*-
"""Example plugin Settings chapter."""
from activity_browser.plugins import BaseSettingsChapter
from qtpy import QtWidgets


class ExampleSettingsChapter(BaseSettingsChapter):
    plugin_settings = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.greeting = QtWidgets.QLineEdit()
        self.greeting.setPlaceholderText("Greeting stored in plugin settings")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Plugin Example preferences"))
        layout.addWidget(self.greeting)
        layout.addStretch()
        self.greeting.textChanged.connect(lambda: self.changed.emit())
        self.reset()

    def get_current_state(self):
        return {"greeting": self.greeting.text()}

    def reset(self):
        data = ExampleSettingsChapter.plugin_settings
        text = "Hello from Plugin Example"
        if data is not None:
            text = data.get("greeting", text)
        self.greeting.setText(text)
        self._initial_state = self.get_current_state()

    def set_settings(self):
        data = ExampleSettingsChapter.plugin_settings
        if data is not None:
            data["greeting"] = self.greeting.text()
