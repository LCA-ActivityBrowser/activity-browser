from PySide2 import QtWidgets

from activity_browser import application, log, signals
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class CSNew(ABAction):
    """
    ABAction to create a new Calculation Setup. Prompts the user for a name for the new CS. Returns if the user cancels,
    or when a CS with the same name is already present within the project. Otherwise, instructs the CSController to
    create a new Calculation Setup with the given name.
    """
    icon = qicons.add
    text = "New"

    @staticmethod
    @exception_dialogs
    def run():
        # prompt the user to give a name for the new calculation setup
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )

        # return if the user cancels or gives no name
        if not ok or not name: return

        # throw error if the name is already present, and return
        if name in bd.calculation_setups:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        # instruct the CalculationSetupController to create a CS with the new name
        bd.calculation_setups[name] = {'inv': [], 'ia': []}
        signals.calculation_setup_selected.emit(name)
        log.info(f"New calculation setup: {name}")
