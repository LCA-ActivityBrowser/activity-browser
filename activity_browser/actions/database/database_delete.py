from typing import List

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
    Deletes one or more databases from the project after user confirmation.

    This method performs the following steps:
    - Displays a confirmation dialog to the user with the database name(s) and total record count.
    - If the user confirms, deletes the database(s), their upstream exchanges, and associated parameters.
    - Removes the database(s) from the project settings.

    Args:
        db_names (List[str]): The name(s) of the database(s) to be deleted.

    Steps:
    - Set the cursor to a waiting state while gathering data for large databases.
    - Retrieve the record count for the specified database(s).
    - Construct a warning message with the database name(s) and record count.
    - Display a confirmation dialog to the user.
    - If the user cancels, exit the method.
    - Set the cursor to a waiting state while performing the deletion.
    - Delete upstream exchanges associated with the database(s).
    - Remove the database(s) from the Brightway2 project.
    - Delete database parameters.
    - Remove the database(s) from the project settings.
    - Restore the cursor to its default state.
    """

    icon = qicons.delete
    text = "Delete databases"
    tool_tip = "Delete database(s) from the project"

    @staticmethod
    @exception_dialogs
    def run(db_names: List[str]):
        # gathering data will take time for large databases
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # get the total record count from all databases
        total_records = 0
        for db_name in db_names:
            n_records = AB_metadata.dataframe[AB_metadata.dataframe["database"] == db_name].shape[0]
            total_records += n_records

        # construct warning text
        if len(db_names) == 1:
            text = f"Are you sure you want to delete database <b>'{db_names[0]}'</b>?"
            if total_records:
                text += f" It contains {total_records} activities."
        else:
            text = f"Are you sure you want to delete {len(db_names)} databases?"
            if total_records:
                text += f" They contain {total_records} activities in total."

        # ask the user for confirmation
        QtWidgets.QApplication.restoreOverrideCursor()
        response = QtWidgets.QMessageBox.question(
            application.main_window, build_title(db_names), text
        )

        # return if the user cancels
        if response != QtWidgets.QMessageBox.Yes:
            return

        # deleting data will take time for large databases
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        for db_name in db_names:
            # delete upstream exchanges
            ExchangeDataset.delete().where(ExchangeDataset.input_database == db_name).execute()

            # instruct the DatabaseController to delete the database from the project.
            del bd.databases[db_name]

            # delete database parameters
            Group.delete().where(Group.name == db_name).execute()

            # remove database from project settings
            settings.project_settings.remove_db(db_name)

        QtWidgets.QApplication.restoreOverrideCursor()


def build_title(db_names: List[str]) -> str:
    """Build an appropriate title for the confirmation dialog."""
    if len(db_names) == 1:
        return "Delete database?"
    return "Delete databases?"
