from typing import Callable, Union

from PySide2 import QtCore

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.bw2data import get_activity
from activity_browser.ui.icons import qicons


class ActivityModify(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """

    icon = qicons.edit
    text = "Modify Activity"

    @staticmethod
    @exception_dialogs
    def run(activity_key: tuple, field: str, value: any):
        activity = get_activity(activity_key)
        activity[field] = value
        activity.save()
