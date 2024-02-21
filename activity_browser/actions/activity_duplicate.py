from typing import Union, Callable

from PySide2 import QtCore

from ..controllers.activity import activity_controller
from ..ui.icons import qicons
from .base import ABAction


class ActivityDuplicate(ABAction):
    icon = qicons.copy
    title = 'Duplicate ***'
    activity_keys: list[tuple]

    def __init__(self, activity_keys: Union[list[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        activity_controller.duplicate_activities(self.activity_keys)


