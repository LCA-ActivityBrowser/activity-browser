from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class CSDelete(ABAction):
    """
    ABAction to delete a calculation setup. First asks the user for confirmation and returns if cancelled. Otherwise,
    passes the csname to the CalculationSetupController for deletion. Finally, displays confirmation that it succeeded.
    """

    icon = qicons.delete
    text = "Delete"

    @staticmethod
    @exception_dialogs
    def run(cs_names: str | list[str]):
        if isinstance(cs_names, str):
            cs_names = [cs_names]

        # ask the user whether they are sure to delete the calculation setup
        warning = QtWidgets.QMessageBox.warning(
            application.main_window,
            f"Deleting Calculation Setup(s): {', '.join(cs_names)}",
            "Are you sure?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        # return if the users cancels
        if warning == QtWidgets.QMessageBox.No:
            return

        for cs_name in cs_names:
            if cs_name not in bd.calculation_setups:
                log.warning(f"Calculation setup {cs_name} not found")
                continue

            del bd.calculation_setups[cs_name]
            log.info(f"Deleted calculation setup: {cs_name}")
