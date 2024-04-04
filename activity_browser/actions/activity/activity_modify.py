from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import application, activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityModify(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """
    icon = qicons.edit
    title = 'Modify Activity'
    activity_key: tuple
    field: str
    value: any

    def __init__(self,
                 activity_key: Union[tuple, Callable],
                 field: Union[str, Callable],
                 value: Union[any, Callable],
                 parent: QtCore.QObject):
        super().__init__(parent, activity_key=activity_key, field=field, value=value)

    def onTrigger(self, toggled):
        activity = activity_controller.get(self.activity_key)
        activity[self.field] = self.value
        activity.save()
