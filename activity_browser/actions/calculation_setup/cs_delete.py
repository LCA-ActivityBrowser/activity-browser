import traceback
from typing import Union, Callable

from PySide2 import QtCore, QtWidgets

from activity_browser import application, log
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.controllers import calculation_setup_controller


class CSDelete(ABAction):
    """
    ABAction to delete a calculation setup. First asks the user for confirmation and returns if cancelled. Otherwise,
    passes the csname to the CalculationSetupController for deletion. Finally, displays confirmation that it succeeded.
    """
    icon = qicons.delete
    title = "Delete"
    cs_name: str

    def __init__(self, cs_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, cs_name=cs_name)

    def onTrigger(self, toggled):
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(application.main_window,
                                                f"Deleting Calculation Setup: {self.cs_name}",
                                                "Are you sure you want to delete this calculation setup?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.No
                                                )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        try:
            calculation_setup_controller.delete_calculation_setup(self.cs_name)
        except Exception as e:
            log.error(f"Deletion of calculation setup {self.cs_name} failed with error {traceback.format_exc()}")
            QtWidgets.QMessageBox.critical(application.main_window,
                                           f"Deleting Calculation Setup: {self.cs_name}",
                                           "An error occured during the deletion of the calculation setup. Check the "
                                           "logs for more information",
                                           QtWidgets.QMessageBox.Ok
                                           )
            return

        QtWidgets.QMessageBox.information(application.main_window,
                                          f"Deleting Calculation Setup: {self.cs_name}",
                                          "Calculation setup was succesfully deleted.",
                                          QtWidgets.QMessageBox.Ok)

