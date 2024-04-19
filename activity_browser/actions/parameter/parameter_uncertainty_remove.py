from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data import parameters
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.bwutils import uncertainty


class ParameterUncertaintyRemove(ABAction):
    """
    ABAction to delete an existing parameter.
    """
    icon = qicons.delete
    title = "Remove parameter uncertainty"
    parameter: Any

    def __init__(self,
                 parameter: Union[Any, Callable],
                 parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter)

    def onTrigger(self, toggled):
        self.parameter.data.update(uncertainty.EMPTY_UNCERTAINTY)
        self.parameter.save()
        parameters.recalculate()
