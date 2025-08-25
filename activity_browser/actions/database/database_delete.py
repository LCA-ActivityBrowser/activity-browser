from qtpy import QtCore, QtWidgets

import bw2data as bd
from bw2data.parameters import Group
from bw2data.backends.proxies import ExchangeDataset, Exchanges

from activity_browser import application, settings
from activity_browser.bwutils import AB_metadata
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class DatabaseDelete(ABAction):
    """
    Deletes a specified database from the project after user confirmation.

    This method performs the following steps:
    - Displays a confirmation dialog to the user with the database name and record count.
    - If the user confirms, deletes the database, its upstream exchanges, and associated parameters.
    - Removes the database from the project settings.

    Args:
        db_name (str): The name of the database to be deleted.

    Steps:
    - Set the cursor to a waiting state while gathering data for large databases.
    - Retrieve the record count for the specified database.
    - Construct a warning message with the database name and record count.
    - Display a confirmation dialog to the user.
    - If the user cancels, exit the method.
    - Set the cursor to a waiting state while performing the deletion.
    - Delete upstream exchanges associated with the database.
    - Remove the database from the Brightway2 project.
    - Delete database parameters.
    - Remove the database from the project settings.
    - Restore the cursor to its default state.
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
        n_records = AB_metadata.dataframe[AB_metadata.dataframe["database"] == db_name].shape[0]

        # construct warning text
        text = f"Are you sure you want to delete database '{db_name}'?"
        if n_records:
            text += f" It contains {n_records} activities"

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
        ExchangeDataset.delete().where(ExchangeDataset.input_database == db_name).execute()

        # instruct the DatabaseController to delete the database from the project.
        del bd.databases[db_name]

        # delete database parameters
        Group.delete().where(Group.name == db_name).execute()

        # remove database from project settings
        settings.project_settings.remove_db(db_name)

        QtWidgets.QApplication.restoreOverrideCursor()
