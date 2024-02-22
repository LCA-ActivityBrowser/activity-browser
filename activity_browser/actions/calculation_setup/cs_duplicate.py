from typing import Union, Callable, Any

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.controllers import calculation_setup_controller


class CSDuplicate(ABAction):
    icon = qicons.copy
    title = "Duplicate"
    cs_name: str

    def __init__(self, cs_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, cs_name=cs_name)

    def onTrigger(self, toggled):
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Duplicate '{self.cs_name}'",
            "Name of the duplicated calculation setup:" + " " * 10
        )

        if not ok or not new_name: return

        if new_name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        calculation_setup_controller.duplicate_calculation_setup(self.cs_name, new_name)
