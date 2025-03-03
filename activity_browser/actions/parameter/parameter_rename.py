from qtpy import QtWidgets

from bw2data.parameters import ParameterBase, parameters

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.bwutils import Parameter, refresh_parameter


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
    def run(parameter: tuple | Parameter | ParameterBase, new_name: str = None):
        parameter = refresh_parameter(parameter)

        new_name = new_name or ParameterRename.get_new_name(parameter)

        if not new_name:
            return

        if not new_name.isidentifier():
            raise ValueError("Parameter name must be a valid Python identifier")

        getattr(parameters, f"rename_{parameter.param_type}_parameter")(
                parameter.to_peewee_model(), new_name, update_dependencies=True
            )

    @staticmethod
    def get_new_name(parameter: Parameter):
        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Rename parameter",
            f"Rename parameter '{parameter.name}' to:",
        )

        if ok and new_name:
            return new_name
