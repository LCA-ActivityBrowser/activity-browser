from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser.controllers.activity import activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityDuplicate(ABAction):
    icon = qicons.copy
    title = 'Duplicate ***'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        activity_controller.duplicate_activities(self.activity_keys)


