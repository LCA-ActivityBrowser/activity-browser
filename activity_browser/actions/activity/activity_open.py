from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser import signals
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityOpen(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """
    icon = qicons.right
    title = 'Open ***'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        for key in self.activity_keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)
