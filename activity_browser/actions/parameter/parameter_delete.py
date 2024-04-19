from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data import get_activity
from activity_browser.brightway.bw2data.parameters import ActivityParameter, Group, parameters
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterDelete(ABAction):
    """
    ABAction to delete an existing parameter.
    """
    icon = qicons.delete
    title = "Delete parameter..."
    parameter: Any

    def __init__(self, parameter: Union[Any, Callable], parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter)

    def onTrigger(self, toggled):
        if isinstance(self.parameter, ActivityParameter):
            db = self.parameter.database
            code = self.parameter.code
            amount = (ActivityParameter.select()
                      .where(ActivityParameter.database == db & ActivityParameter.code == code)
                      .count())

            if amount > 1:
                self.parameter.delete_instance()
            else:
                group = self.parameter.group
                act = get_activity((db, code))
                parameters.remove_from_group(group, act)
                # Also clear the group if there are no more parameters in it
                exists = (ActivityParameter.select()
                          .where(ActivityParameter.group == group).exists())
                if not exists:
                    Group.delete().where(Group.name == group).execute()
        else:
            self.parameter.delete_instance()
        # After deleting things, recalculate and signal changes
        parameters.recalculate()
