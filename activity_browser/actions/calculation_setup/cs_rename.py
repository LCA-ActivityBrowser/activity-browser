from typing import Union, Callable

from PySide2 import QtCore, QtWidgets

from activity_browser import application, cs_controller, signals, log
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class CSRename(ABAction):
    """
    ABAction to rename a calculation setup. Prompts the user for a new name. Returns if the user cancels, or if a CS
    with the same name is already present within the project. If all is right, instructs the CalculationSetupController
    to rename the CS.
    """
    icon = qicons.edit
    title = "Rename"
    cs_name: str

    def __init__(self, cs_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, cs_name=cs_name)

    def onTrigger(self, toggled):
        # prompt the user to give a name for the new calculation setup
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Rename '{self.cs_name}'",
            "New name of this calculation setup:" + " " * 10
        )

        # return if the user cancels or gives no name
        if not ok or not new_name: return

        # throw error if the name is already present, and return
        if new_name in cs_controller.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        # instruct the CalculationSetupController to rename the CS to the new name
        cs_controller[new_name] = cs_controller[self.cs_name].copy()
        del cs_controller[self.cs_name]
        signals.calculation_setup_selected.emit(new_name)
        log.info(f"Renamed calculation setup from {self.cs_name} to {new_name}")
