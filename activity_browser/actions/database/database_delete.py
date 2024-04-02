from typing import Union, Callable

from PySide2 import QtWidgets, QtCore
from bw2data.parameters import Group

from activity_browser import application, database_controller, project_settings
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class DatabaseDelete(ABAction):
    """
    ABAction to delete a database from the project. Asks the user for confirmation. If confirmed, instructs the
    DatabaseController to delete the database in question.
    """
    icon = qicons.delete
    title = "Delete database"
    tool_tip = "Delete this database from the project"
    db_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, db_name=database_name)

    def onTrigger(self, toggled):
        # get the record count from the database controller
        database = database_controller.get(self.db_name)
        n_records = len(database)

        # ask the user for confirmation
        response = QtWidgets.QMessageBox.question(
            application.main_window,
            "Delete database?",
            f"Are you sure you want to delete database '{self.db_name}'? It contains {n_records} activities"
        )

        # return if the user cancels
        if response != response.Yes: return

        # instruct the DatabaseController to delete the database from the project.
        del database_controller[self.db_name]

        Group.delete().where(Group.name == self.db_name).execute()
        project_settings.remove_db(self.db_name)

