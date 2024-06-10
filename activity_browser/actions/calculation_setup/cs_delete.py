import traceback

from PySide2 import QtWidgets

from activity_browser import application, log, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CSDelete(ABAction):
    """
    ABAction to delete a calculation setup. First asks the user for confirmation and returns if cancelled. Otherwise,
    passes the csname to the CalculationSetupController for deletion. Finally, displays confirmation that it succeeded.
    """

    icon = qicons.delete
    text = "Delete"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str):
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(
            application.main_window,
            f"Deleting Calculation Setup: {cs_name}",
            "Are you sure you want to delete this calculation setup?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No:
            return

        del bd.calculation_setups[cs_name]
        signals.set_default_calculation_setup.emit()
        log.info(f"Deleted calculation setup: {cs_name}")

        QtWidgets.QMessageBox.information(
            application.main_window,
            f"Deleting Calculation Setup: {cs_name}",
            "Calculation setup was succesfully deleted.",
            QtWidgets.QMessageBox.Ok,
        )
