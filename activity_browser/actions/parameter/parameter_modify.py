from typing import Any

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.bw2data import parameters
from activity_browser.ui.icons import qicons


class ParameterModify(ABAction):
    """
    ABAction to delete an existing parameter.
    """

    icon = qicons.edit
    text = "Modify Parameter"

    @staticmethod
    @exception_dialogs
    def run(parameter: Any, field: str, value: any):
        if field == "data":
            parameter.data.update(value)
        else:
            setattr(parameter, field, value)
        parameter.save()

        parameters.recalculate()
