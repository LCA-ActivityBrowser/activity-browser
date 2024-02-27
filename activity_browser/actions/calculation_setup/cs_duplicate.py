from typing import Union, Callable

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application, calculation_setup_controller
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class CSDuplicate(ABAction):
    """
    ABAction to duplicate a calculation setup. Prompts the user for a new name. Returns if the user cancels, or if a CS
    with the same name is already present within the project. If all is right, instructs the CalculationSetupController
    to duplicate the CS.
    """
    icon = qicons.copy
    title = "Duplicate"
    cs_name: str

    def __init__(self, cs_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, cs_name=cs_name)

    def onTrigger(self, toggled):
        # prompt the user to give a name for the new calculation setup
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Duplicate '{self.cs_name}'",
            "Name of the duplicated calculation setup:" + " " * 10
        )

        # return if the user cancels or gives no name
        if not ok or not new_name: return

        # throw error if the name is already present, and return
        if new_name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        # instruct the CalculationSetupController to duplicate the CS to the new name
        calculation_setup_controller.duplicate_calculation_setup(self.cs_name, new_name)
