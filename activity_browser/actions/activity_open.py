from typing import Union, Callable

from PySide2 import QtCore

from activity_browser import signals
from ..ui.icons import qicons
from .base import ABAction


class ActivityOpen(ABAction):
    icon = qicons.right
    title = 'Open ***'
    activity_keys: list[tuple]

    def __init__(self, activity_keys: Union[list[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        for key in self.activity_keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)
