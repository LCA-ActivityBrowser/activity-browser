from typing import List

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivityGraph(ABAction):
    """
    ABAction to open one or multiple activities in the graph explorer
    """

    icon = qicons.graph_explorer
    text = "Open in Graph Explorer"

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        for key in activity_keys:
            signals.open_activity_graph_tab.emit(key)
