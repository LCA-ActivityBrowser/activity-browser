from typing import Union, Callable, Any

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..controllers import database_controller


class DatabaseDelete(ABAction):
    icon = qicons.delete
    title = "Delete database"
    tool_tip = "Delete this database from the project"
    db_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, db_name=database_name)

    def onTrigger(self, toggled):
        n_records = database_controller.record_count(self.db_name)

        response = QtWidgets.QMessageBox.question(
            application.main_window,
            "Delete database?",
            f"Are you sure you want to delete database '{self.db_name}'? It contains {n_records} activities"
        )

        if response != response.Yes: return

        database_controller.delete_database(self.db_name)

