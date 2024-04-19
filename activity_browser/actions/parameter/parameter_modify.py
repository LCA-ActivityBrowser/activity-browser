from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data import parameters
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterModify(ABAction):
    """
    ABAction to delete an existing parameter.
    """
    icon = qicons.edit
    title = "Modify Parameter"
    parameter: Any
    field: str
    value: any

    def __init__(self,
                 parameter: Union[Any, Callable],
                 field: Union[str, Callable],
                 value: Union[any, Callable],
                 parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter, field=field, value=value)

    def onTrigger(self, toggled):
        if self.field == "data":
            self.parameter.data.update(self.value)
        else:
            setattr(self.parameter, self.field, self.value)
        self.parameter.save()

        parameters.recalculate()
