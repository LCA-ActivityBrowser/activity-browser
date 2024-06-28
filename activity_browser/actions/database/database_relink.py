from PySide2 import QtCore, QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.strategies import relink_exchanges_existing_db
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets import (DatabaseLinkingDialog,
                                         DatabaseLinkingResultsDialog)


class DatabaseRelink(ABAction):
    """
    ABAction to relink the dependencies of a database.
    """

    icon = qicons.edit
    text = "Relink the database"
    tool_tip = "Relink the dependencies of this database"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        db_name = db_name
        # get brightway database object
        db = bd.Database(db_name)

        # find the dependencies of the database and construct a list of suitable candidates
        depends = db.find_dependents()
        options = [(depend, list(bd.databases)) for depend in depends]

        # construct a dialog in which the user chan choose which depending database to connect to which candidate
        dialog = DatabaseLinkingDialog.relink_sqlite(
            db_name, options, application.main_window
        )

        # return if the user cancels
        if dialog.exec_() != DatabaseLinkingDialog.Accepted:
            return

        # else, start the relinking
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        relinking_results = dict()

        # relink using relink_exchanges_existing_db strategy
        for old, new in dialog.relink.items():
            other = bd.Database(new)
            failed, succeeded, examples = relink_exchanges_existing_db(db, old, other)
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        QtWidgets.QApplication.restoreOverrideCursor()

        # if any failed, present user with results dialog
        if failed > 0:
            relinking_dialog = DatabaseLinkingResultsDialog.present_relinking_results(
                application.main_window, relinking_results, examples
            )
            relinking_dialog.exec_()
            relinking_dialog.open_activity()
