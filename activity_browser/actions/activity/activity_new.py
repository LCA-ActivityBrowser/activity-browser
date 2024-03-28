from typing import Union, Callable

from PySide2 import QtWidgets, QtCore

from activity_browser import application, activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityNew(ABAction):
    """
    ABAction to create a new activity. Prompts the user to supply a name. Returns if no name is supplied or if the user
    cancels. Otherwise, instructs the ActivityController to create a new activity.
    """
    icon = qicons.add
    title = "New activity"
    database_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, database_name=database_name)

    def onTrigger(self, toggled):
        # ask the user to provide a name for the new activity
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
            QtWidgets.QLineEdit.Normal
        )

        # if no name is provided, or the user cancels, return
        if not ok or not name: return

        # else, instruct the ActivityController to create a new activity
        activity_controller.new_activity(self.database_name, name)
