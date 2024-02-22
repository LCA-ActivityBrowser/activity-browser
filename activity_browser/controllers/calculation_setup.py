import brightway2 as bw
from PySide2.QtCore import QObject

from activity_browser import log, signals, application


class CalculationSetupController(QObject):
    """The controller that handles brightway features related to
    calculation setups.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def new_calculation_setup(self, name) -> None:
        bw.calculation_setups[name] = {'inv': [], 'ia': []}
        signals.calculation_setup_selected.emit(name)
        log.info("New calculation setup: {}".format(name))

    def duplicate_calculation_setup(self, cs_name: str, new_name: str) -> None:
        bw.calculation_setups[new_name] = bw.calculation_setups[cs_name].copy()
        signals.calculation_setup_selected.emit(new_name)
        log.info("Copied calculation setup {} as {}".format(cs_name, new_name))

    def delete_calculation_setup(self, cs_name: str) -> None:
        del bw.calculation_setups[cs_name]
        signals.set_default_calculation_setup.emit()
        signals.delete_calculation_setup.emit(cs_name)
        log.info(f"Deleted calculation setup: {cs_name}")

    def rename_calculation_setup(self, cs_name: str, new_name: str) -> None:
        bw.calculation_setups[new_name] = bw.calculation_setups[cs_name].copy()
        del bw.calculation_setups[cs_name]
        signals.calculation_setup_selected.emit(new_name)
        log.info("Renamed calculation setup from {} to {}".format(cs_name, new_name))


calculation_setup_controller = CalculationSetupController(application)
