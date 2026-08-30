# -*- coding: utf-8 -*-
"""Example plugin page."""
from activity_browser.plugins import ABAbstractPage
from qtpy import QtWidgets

from . import project_status


class ExamplePage(ABAbstractPage):
    title = "Plugin Example"
    basePage = True

    def __init__(self, *args, settings=None, signals=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._plugin_settings = settings
        self._host_signals = signals

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "This page was registered by the Plugin Example sample.\n"
                "See plugins/ab-plugin-example/ab_example/activate.py for wiring."
            )
        )
        self.project_status = QtWidgets.QLabel()
        layout.addWidget(self.project_status)
        self.settings_echo = QtWidgets.QLabel()
        layout.addWidget(self.settings_echo)
        layout.addStretch()

        if self._host_signals is not None:
            self._host_signals.project.changed.connect(self._refresh_project_status)
        self._refresh_project_status()

    def _refresh_project_status(self, *args):
        self.project_status.setText(
            f"Current project: {project_status.current_project_label()}"
        )

    def showEvent(self, event):
        data = self._plugin_settings
        greeting = "(default)"
        if data is not None:
            greeting = data.get("greeting", greeting)
        self.settings_echo.setText(f"Namespaced setting 'greeting': {greeting}")
        self._refresh_project_status()
        super().showEvent(event)
