from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data import parameters
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterUncertaintyModify(ABAction):
    """
    ABAction to delete an existing parameter.
    """
    icon = qicons.delete
    title = "Remove parameter uncertainty"
    parameter: Any
    uncertainty_dict: dict

    def __init__(self,
                 parameter: Union[Any, Callable],
                 uncertainty_dict: [dict, Callable],
                 parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter, uncertainty_dict=uncertainty_dict)

    def onTrigger(self, toggled):
        self.parameter.data.update(self.uncertainty_dict)
        self.parameter.save()
        parameters.recalculate()
