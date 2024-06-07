from typing import Any

from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.mod.bw2data.parameters import parameters, ActivityParameter, DatabaseParameter, ProjectParameter
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ParameterRename(ABAction):
    """
    ABAction to rename an existing parameter. Constructs a dialog for the user in which they choose the new name. If no
    name is chosen, or the user cancels: return. Else, instruct the ParameterController to rename the parameter using
    the given name.
    """
    icon = qicons.edit
    text = "Rename parameter..."

    @staticmethod
    @exception_dialogs
    def run(parameter: Any):
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Rename parameter",
            f"Rename parameter '{parameter.name}' to:"
        )

        if not ok or not new_name: return

        try:
            if isinstance(parameter, ProjectParameter):
                parameters.rename_project_parameter(parameter, new_name, update_dependencies=True)
            if isinstance(parameter, DatabaseParameter):
                parameters.rename_database_parameter(parameter, new_name, update_dependencies=True)
            if isinstance(parameter, ActivityParameter):
                parameters.rename_activity_parameter(parameter, new_name, update_dependencies=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                application.main_window, "Could not save changes", str(e),
                QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
            )
