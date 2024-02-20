from PySide2 import QtWidgets

from activity_browser import application
from ..controllers.activity import activity_controller
from ..ui.icons import qicons
from .base import ABAction


class ActivityNew(ABAction):
    icon = qicons.add
    title = "New activity"
    depends = ["current_database"]

    def onTrigger(self, toggled):
        database_name = self.parent().current_database

        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
        )

        if not ok or not name: return

        activity_controller.new_activity(database_name, name)
