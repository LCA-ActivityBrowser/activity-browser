from typing import Union, Callable

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.controllers.activity import activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityNew(ABAction):
    icon = qicons.add
    title = "New activity"
    database_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, database_name=database_name)

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
            QtWidgets.QLineEdit.Normal
        )

        if not ok or not name: return

        activity_controller.new_activity(self.database_name, name)
