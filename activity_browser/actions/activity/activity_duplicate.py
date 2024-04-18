from typing import Union, Callable, List
import cProfile

from PySide2 import QtCore

from activity_browser.brightway.bw2data import get_activity
from activity_browser.bwutils import commontasks
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityDuplicate(ABAction):
    """
    Duplicate one or multiple activities using their keys. Proxy action to call the controller.
    """
    icon = qicons.copy
    title = 'Duplicate ***'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        activities = [get_activity(key) for key in self.activity_keys]

        for activity in activities:
            new_code = commontasks.generate_copy_code(activity.key)
            activity.copy(new_code)

