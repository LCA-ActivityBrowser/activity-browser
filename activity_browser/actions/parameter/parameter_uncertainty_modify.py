from typing import Any

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ParameterUncertaintyModify(ABAction):
    """
    ABAction to modify the uncertainty of an existing parameter.
    """

    icon = qicons.edit
    text = "Modify parameter uncertainty"

    @staticmethod
    @exception_dialogs
    def run(parameter: Any, uncertainty_dict: dict):
        parameter.data.update(uncertainty_dict)
        parameter.save()
        bd.parameters.recalculate()
