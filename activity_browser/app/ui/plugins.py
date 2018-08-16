# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets
from ..signals import signals


class PluginManager():
    """
    Starts Plugins for now. Probably gets more functionality in the future.
    """

    def __init__(self, window):
        self.window = window
        self.connect_signals()

    def connect_signals(self):
        signals.launch_plugin_lcopt.connect(self.open_lcopt)

    def open_lcopt(self):
        try:
            from activity_browser.app.ui.web.lcopt import LcoptWidget
        except ImportError:
            QtWidgets.QMessageBox.warning(self.window, "ImportError", "Could not load plugin.")
            return

        if not hasattr(self, 'lcopt_window'):
            self.lcopt_window = LcoptWidget()
        self.window.stacked.addWidget(self.lcopt_window)
        self.window.stacked.setCurrentWidget(self.lcopt_window)
        signals.update_windows.emit()
