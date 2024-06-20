from bw2data.parameters import Group
from PySide2 import QtCore, QtWidgets

from activity_browser import application, project_settings
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.backends.proxies import (ExchangeDataset,
                                                           Exchanges)
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
        # gathering data will take time for large databases
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # get the record count from the database controller
        db_name = db_name
        database = bd.Database(db_name)
        n_records = len(database)

        # get any upstream exchanges (hacky because Brightway doesn't do this itself)
        excs = Exchanges((db_name, None))
        excs._args = [
            ExchangeDataset.input_database == db_name,
            ExchangeDataset.output_database != db_name,
        ]
        n_upstream_excs = len(excs)

        # construct warning text
        text = f"Are you sure you want to delete database '{db_name}'?"
        if n_records:
            text += f" It contains {n_records} activities"
        if n_upstream_excs:
            text += f" and {n_upstream_excs} exchanges to other databases"

        # ask the user for confirmation
        QtWidgets.QApplication.restoreOverrideCursor()
        response = QtWidgets.QMessageBox.question(
            application.main_window, "Delete database?", text
        )

        # return if the user cancels
        if response != response.Yes:
            return

        # deleting data will take time for large databases
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # delete upstream exchanges
        excs.delete()

        # instruct the DatabaseController to delete the database from the project.
        del bd.databases[db_name]

        # delete database parameters
        Group.delete().where(Group.name == db_name).execute()

        # remove database from project settings
        project_settings.remove_db(db_name)

        QtWidgets.QApplication.restoreOverrideCursor()
