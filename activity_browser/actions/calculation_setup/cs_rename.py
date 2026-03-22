from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSRename(ABAction):
    """
    ABAction to rename a calculation setup. Prompts the user for a new name. Returns if the user cancels, or if a CS
    with the same name is already present within the project. If all is right, instructs the CalculationSetupController
    to rename the CS.
    """

    icon = qicons.edit
    text = "Rename"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str, new_name: str = None):
        # prompt the user to give a name for the new calculation setup
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Rename '{cs_name}'",
            "New name of this calculation setup:" + " " * 10,
        )

        # return if the user cancels or gives no name
        if not ok or not new_name:
            return

        # throw error if the name is already present, and return
        if new_name in bd.calculation_setups:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists.",
            )
            return

        # instruct the CalculationSetupController to rename the CS to the new name
        bd.calculation_setups[new_name] = bd.calculation_setups[cs_name].copy()
        del bd.calculation_setups[cs_name]
        signals.calculation_setup_selected.emit(new_name)
        log.info(f"Renamed calculation setup from {cs_name} to {new_name}")
