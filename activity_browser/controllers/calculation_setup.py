import traceback

import brightway2 as bw
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser import log, signals, application


class CalculationSetupController(QObject):
    """The controller that handles brightway features related to
    calculation setups.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        signals.new_calculation_setup.connect(self.new_calculation_setup)
        signals.copy_calculation_setup.connect(self.copy_calculation_setup)
        signals.rename_calculation_setup.connect(self.rename_calculation_setup)
        signals.delete_calculation_setup.connect(self.delete_calculation_setup)

    @Slot(name="createCalculationSetup")
    def new_calculation_setup(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if ok and name:
            if not self._can_use_cs_name(name):
                return
            bw.calculation_setups[name] = {'inv': [], 'ia': []}
            signals.calculation_setup_selected.emit(name)
            log.info("New calculation setup: {}".format(name))

    @Slot(str, name="copyCalculationSetup")
    def copy_calculation_setup(self, current: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Copy '{}'".format(current),
            "Name of the copied calculation setup:" + " " * 10
        )
        if ok and new_name:
            if not self._can_use_cs_name(new_name):
                return
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            signals.calculation_setup_selected.emit(new_name)
            log.info("Copied calculation setup {} as {}".format(current, new_name))

    @Slot(str, name="deleteCalculationSetup")
    def delete_calculation_setup(self, name: str) -> None:
        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(application.main_window,
            f"Deleting Calculation Setup: {name}",
            "Are you sure you want to delete this calculation setup?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        
        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No: return

        # otherwise try to delete the calculation setup
        try:
            del bw.calculation_setups[name]
            signals.set_default_calculation_setup.emit()
        # if an error occurs, notify the user and return
        except Exception as e:
            log.error(f"Deletion of calculation setup {name} failed with error {traceback.format_exc()}")
            QtWidgets.QMessageBox.critical(application.main_window,
                f"Deleting Calculation Setup: {name}",
                "An error occured during the deletion of the calculation setup. Check the logs for more information",
                QtWidgets.QMessageBox.Ok)
            return

        # inform the user that the calculation setup has been deleted
        log.info(f"Deleted calculation setup: {name}")
        QtWidgets.QMessageBox.information(application.main_window,
            f"Deleting Calculation Setup: {name}",
            "Calculation setup was succesfully deleted.",
            QtWidgets.QMessageBox.Ok)

    @Slot(str, name="renameCalculationSetup")
    def rename_calculation_setup(self, current: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Rename '{}'".format(current),
            "New name of this calculation setup:" + " " * 10
        )
        if ok and new_name:
            if not self._can_use_cs_name(new_name):
                return
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            del bw.calculation_setups[current]
            signals.calculation_setup_selected.emit(new_name)
            log.info("Renamed calculation setup from {} to {}".format(current, new_name))

    def _can_use_cs_name(self, new_name: str) -> bool:
        if new_name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window, "Not possible",
                "A calculation setup with this name already exists."
            )
            return False
        return True

calculation_setup_controller = CalculationSetupController(application)
