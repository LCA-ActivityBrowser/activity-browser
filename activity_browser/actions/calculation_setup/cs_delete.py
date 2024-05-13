import traceback

from PySide2 import QtWidgets

from activity_browser import application, log, signals
from activity_browser.brightway import bd
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class CSDelete(NewABAction):
    """
    ABAction to delete a calculation setup. First asks the user for confirmation and returns if cancelled. Otherwise,
    passes the csname to the CalculationSetupController for deletion. Finally, displays confirmation that it succeeded.
    """
    icon = qicons.delete
    text = "Delete"

    @staticmethod
    def run(cs_name: str):
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(application.main_window,
                                                f"Deleting Calculation Setup: {cs_name}",
                                                "Are you sure you want to delete this calculation setup?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.No
                                                )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        try:
            del bd.calculation_setups[cs_name]
            signals.set_default_calculation_setup.emit()
            log.info(f"Deleted calculation setup: {cs_name}")
        except Exception as e:
            log.error(f"Deletion of calculation setup {cs_name} failed with error {traceback.format_exc()}")
            QtWidgets.QMessageBox.critical(application.main_window,
                                           f"Deleting Calculation Setup: {cs_name}",
                                           "An error occured during the deletion of the calculation setup. Check the "
                                           "logs for more information",
                                           QtWidgets.QMessageBox.Ok
                                           )
            return

        QtWidgets.QMessageBox.information(application.main_window,
                                          f"Deleting Calculation Setup: {cs_name}",
                                          "Calculation setup was succesfully deleted.",
                                          QtWidgets.QMessageBox.Ok)

