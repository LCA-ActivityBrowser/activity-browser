from typing import Callable, List, Union

from qtpy import QtCore

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import commontasks
from bw2data import get_activity
from activity_browser.ui.icons import qicons


class ActivityDuplicate(ABAction):
    """
    Duplicate one or multiple activities using their keys. Proxy action to call the controller.
    """

    icon = qicons.copy
    text = "Duplicate ***"

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        activities = [get_activity(key) for key in activity_keys]

        for activity in activities:
            new_code = commontasks.generate_copy_code(activity.key)
            activity.copy(new_code)
