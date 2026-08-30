# -*- coding: utf-8 -*-
"""Example plugin pane."""
from activity_browser.plugins import ABAbstractPane
from qtpy import QtWidgets

from . import project_status


class ExamplePane(ABAbstractPane):
    title = "Plugin Example"
    unique = True

    def __init__(self, parent):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                "Sample plugin pane. Status below updates when the project changes."
            )
        )
        self.status = QtWidgets.QLabel("Current project: (loading…)")
        layout.addWidget(self.status)
        layout.addStretch()

    def sync(self):
        self.status.setText(f"Current project: {project_status.current_project_label()}")
