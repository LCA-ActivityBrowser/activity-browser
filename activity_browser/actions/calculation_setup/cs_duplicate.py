from typing import Union, Callable

from PySide2 import QtCore, QtWidgets

from activity_browser import application, signals, log
from activity_browser.brightway.bw2data import calculation_setups
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
        if new_name in calculation_setups:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        calculation_setups[new_name] = calculation_setups[self.cs_name].copy()
        signals.calculation_setup_selected.emit(new_name)
        log.info(f"Copied calculation setup {self.cs_name} as {new_name}")
