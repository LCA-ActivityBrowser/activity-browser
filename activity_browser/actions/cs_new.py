from typing import Union, Callable, Any

import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser import application
from .base import ABAction
from ..ui.icons import qicons
from ..controllers import calculation_setup_controller


class CSNew(ABAction):
    icon = qicons.add
    title = "New"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )

        if not ok or not name: return

        if name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "Not possible",
                "A calculation setup with this name already exists."
            )
            return

        calculation_setup_controller.new_calculation_setup(name)
