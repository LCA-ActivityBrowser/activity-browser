from typing import List

from qtpy import QtWidgets, QtCore

from activity_browser import signals, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class MethodOpen(ABAction):
    """
    ABAction to open one or more supplied methods in a method tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.right
    text = "Open Impact Category"

    @staticmethod
    @exception_dialogs
    def run(method_names: List[tuple]):
        from activity_browser.layouts import pages

        for name in method_names:
            tab = application.main_window.centralWidget().tabs["Characterization Factors"]
            tab.open_method_tab(name)
