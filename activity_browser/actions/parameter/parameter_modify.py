from typing import Any

from bw2data.parameters import ParameterBase, parameters

from activity_browser.ui.icons import qicons
from activity_browser.bwutils import refresh_parameter, Parameter
from activity_browser.actions.base import ABAction, exception_dialogs

from .parameter_rename import ParameterRename


class ParameterModify(ABAction):
    """
    ABAction to delete an existing parameter.
    """

    icon = qicons.edit
    text = "Modify Parameter"

    @staticmethod
    @exception_dialogs
    def run(parameter: tuple | Parameter | ParameterBase, field: str, value: any):
        parameter = refresh_parameter(parameter)
        param_model = parameter.to_peewee_model()

        if field == "data":
            param_model.data.update(value)
        elif field == "name":
            return ParameterRename.run(parameter, value)
        elif field in dir(param_model):
            setattr(param_model, field, value)
        else:
            param_model.data.update({field: value})

        param_model.save()

        if field in ("amount", "formula"):
            parameters.recalculate()
