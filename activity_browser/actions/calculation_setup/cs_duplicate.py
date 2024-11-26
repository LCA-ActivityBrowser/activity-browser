from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSDuplicate(ABAction):
    """
    ABAction to duplicate a calculation setup. Prompts the user for a new name. Returns if the user cancels, or if a CS
    with the same name is already present within the project. If all is right, instructs the CalculationSetupController
    to duplicate the CS.
    """

    icon = qicons.copy
    text = "Duplicate"

    @staticmethod
    @exception_dialogs
    def run(cs_name: str):
        # prompt the user to give a name for the new calculation setup
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Duplicate '{cs_name}'",
            "Name of the duplicated calculation setup:" + " " * 10,
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

        bd.calculation_setups[new_name] = bd.calculation_setups[cs_name].copy()
        signals.calculation_setup_selected.emit(new_name)
        log.info(f"Copied calculation setup {cs_name} as {new_name}")
