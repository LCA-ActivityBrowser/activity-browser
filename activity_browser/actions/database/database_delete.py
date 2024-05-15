from PySide2 import QtWidgets
from bw2data.parameters import Group

from activity_browser import application, project_settings
from activity_browser.brightway import bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class DatabaseDelete(ABAction):
    """
    ABAction to delete a database from the project. Asks the user for confirmation. If confirmed, instructs the
    DatabaseController to delete the database in question.
    """
    icon = qicons.delete
    text = "Delete database"
    tool_tip = "Delete this database from the project"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        # get the record count from the database controller
        db_name = db_name
        database = bd.Database(db_name)
        n_records = len(database)

        # ask the user for confirmation
        response = QtWidgets.QMessageBox.question(
            application.main_window,
            "Delete database?",
            f"Are you sure you want to delete database '{db_name}'? It contains {n_records} activities"
        )

        # return if the user cancels
        if response != response.Yes: return

        # instruct the DatabaseController to delete the database from the project.
        del bd.databases[db_name]

        Group.delete().where(Group.name == db_name).execute()
        project_settings.remove_db(db_name)
