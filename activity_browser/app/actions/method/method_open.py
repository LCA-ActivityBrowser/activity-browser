from typing import List

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
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
        from activity_browser.app import pages

        for name in method_names:
            page = pages.ImpactCategoryDetailsPage(name)
            central = app.main_window.centralWidget()

            central.addToGroup("Characterization Factors", page)

