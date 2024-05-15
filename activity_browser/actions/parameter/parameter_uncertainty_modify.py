from typing import Any

from activity_browser.brightway import bd
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class ParameterUncertaintyModify(NewABAction):
    """
    ABAction to modify the uncertainty of an existing parameter.
    """
    icon = qicons.edit
    text = "Modify parameter uncertainty"

    @staticmethod
    def run(parameter: Any, uncertainty_dict: dict):
        parameter.data.update(uncertainty_dict)
        parameter.save()
        bd.parameters.recalculate()
