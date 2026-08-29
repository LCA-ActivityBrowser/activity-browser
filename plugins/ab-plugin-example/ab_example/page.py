# -*- coding: utf-8 -*-
"""Example plugin page."""
from activity_browser.plugins import ABAbstractPage
from qtpy import QtWidgets


class ExamplePage(ABAbstractPage):
    title = "Plugin Example"
    basePage = True
    plugin_settings = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "This page was registered by the Plugin Example sample.\n"
                "See plugins/ab-plugin-example/ab_example/activate.py for wiring."
            )
        )
        self.settings_echo = QtWidgets.QLabel()
        layout.addWidget(self.settings_echo)
        layout.addStretch()

    def showEvent(self, event):
        data = ExamplePage.plugin_settings
        greeting = "(default)"
        if data is not None:
            greeting = data.get("greeting", greeting)
        self.settings_echo.setText(f"Namespaced setting 'greeting': {greeting}")
        super().showEvent(event)
