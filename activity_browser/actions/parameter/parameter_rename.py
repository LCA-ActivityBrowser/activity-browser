from typing import Union, Callable, Any

from PySide2 import QtCore, QtWidgets

from activity_browser import application
from activity_browser.controllers import parameter_controller
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterRename(ABAction):
    """
    ABAction to rename an existing parameter. Constructs a dialog for the user in which they choose the new name. If no
    name is chosen, or the user cancels: return. Else, instruct the ParameterController to rename the parameter using
    the given name.
    """
    icon = qicons.edit
    title = "Rename parameter..."
    parameter: Any

    def __init__(self, parameter: Union[Any, Callable], parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter)

    def onTrigger(self, toggled):
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Rename parameter",
            f"Rename parameter '{self.parameter.name}' to:"
        )

        if not ok or not new_name: return

        try:
            parameter_controller.rename_parameter(self.parameter, new_name)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                application.main_window, "Could not save changes", str(e),
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
            )
