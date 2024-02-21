from typing import Union, Callable, Any

import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..controllers import database_controller


class DatabaseNew(ABAction):
    icon = qicons.add
    title = "New database..."
    tool_tip = "Make a new database"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new database",
            "Name of new database:" + " " * 25
        )

        if not ok or not name: return

        if name in bw.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "A database with this name already exists."
            )
            return

        database_controller.new_database(name)
