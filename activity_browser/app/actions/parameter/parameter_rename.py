from qtpy import QtWidgets

from bw2data.parameters import ParameterBase, parameters

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.bwutils.utils import Parameter
from activity_browser.bwutils.commontasks import refresh_parameter
from activity_browser.bwutils.parameters.names import parameter_name_error


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
            return False

        if error := parameter_name_error(new_name):
            QtWidgets.QMessageBox.warning(
                app.main_window, "Invalid parameter name", error
            )
            return False

        getattr(parameters, f"rename_{parameter.param_type}_parameter")(
                parameter.to_peewee_model(), new_name, update_dependencies=True
            )
        return True

    @staticmethod
    def get_new_name(parameter: Parameter):
        new_name, ok = QtWidgets.QInputDialog.getText(
            app.main_window,
            "Rename parameter",
            f"Rename parameter '{parameter.name}' to:",
        )

        if ok and new_name:
            return new_name
