from typing import Union, Callable, List, Tuple

import brightway2 as bw
from activity_browser.bwutils import commontasks as bc
from PySide2 import QtCore, QtWidgets, QtGui

from activity_browser import application, signals
from activity_browser.controllers import parameter_controller
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterNewAutomatic(ABAction):
    icon = qicons.add
    title = "New parameter..."
    activity_keys: List[Tuple]

    def __init__(self, activity_keys: Union[List[Tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        for key in self.activity_keys:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                issue = f"Activity must be 'process' type, '{act.get('name')}' is type '{act.get('type')}'."
                QtWidgets.QMessageBox.warning(
                    application.main_window,
                    "Not allowed",
                    issue,
                    QtWidgets.QMessageBox.Ok,
                    QtWidgets.QMessageBox.Ok
                )
                continue
            parameter_controller.auto_add_parameter(key)

