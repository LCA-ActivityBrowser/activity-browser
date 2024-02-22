from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import signals
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ActivityGraph(ABAction):
    icon = qicons.graph_explorer
    title = "'Open *** in Graph Explorer'"
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        for key in self.activity_keys:
            signals.open_activity_graph_tab.emit(key)
