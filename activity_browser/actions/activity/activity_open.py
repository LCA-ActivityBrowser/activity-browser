from typing import List

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivityOpen(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.right
    text = "Open ***"

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        for key in activity_keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)
