from typing import Union, Callable

from PySide2 import QtCore

from activity_browser import signals
from ..ui.icons import qicons
from .base import ABAction


class ActivityDuplicateToLoc(ABAction):
    icon = qicons.copy
    title = 'Duplicate activity to new location'
    activity_keys: list[tuple]

    def __init__(self, activity_keys: Union[list[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        # TODO: needs a better look because the implementation in the controller is HUGE
        signals.duplicate_activity_new_loc.emit(self.activity_keys)
