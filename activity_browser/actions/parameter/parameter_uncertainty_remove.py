from typing import Any

from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.bwutils import uncertainty


class ParameterUncertaintyRemove(ABAction):
    """
    ABAction to remove the uncertainty of a parameter.
    """
    icon = qicons.delete
    text = "Remove parameter uncertainty"

    @staticmethod
    @exception_dialogs
    def run(parameter: Any):
        parameter.data.update(uncertainty.EMPTY_UNCERTAINTY)
        parameter.save()
        bd.parameters.recalculate()
