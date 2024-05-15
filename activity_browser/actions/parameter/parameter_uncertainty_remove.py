from typing import Any

from activity_browser.brightway import bd
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons
from activity_browser.bwutils import uncertainty


class ParameterUncertaintyRemove(NewABAction):
    """
    ABAction to remove the uncertainty of a parameter.
    """
    icon = qicons.delete
    text = "Remove parameter uncertainty"

    @staticmethod
    def run(parameter: Any):
        parameter.data.update(uncertainty.EMPTY_UNCERTAINTY)
        parameter.save()
        bd.parameters.recalculate()
