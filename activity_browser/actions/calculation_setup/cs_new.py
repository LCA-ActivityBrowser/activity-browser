import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.controllers import calculation_setup_controller


class CSNew(ABAction):
    """
    ABAction to create a new Calculation Setup. Prompts the user for a name for the new CS. Returns if the user cancels,
    or when a CS with the same name is already present within the project. Otherwise, instructs the CSController to
    create a new Calculation Setup with the given name.
    """
    icon = qicons.add
    title = "New"

    def onTrigger(self, toggled):
        # prompt the user to give a name for the new calculation setup
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )

        # return if the user cancels or gives no name
        if not ok or not name: return

        # throw error if the name is already present, and return
        if name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        # instruct the CalculationSetupController to create a CS with the new name
        calculation_setup_controller.new_calculation_setup(name)
