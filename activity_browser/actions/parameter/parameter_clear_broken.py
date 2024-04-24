from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data.parameters import ActivityParameter, Group, GroupDependency, parameters
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ParameterClearBroken(ABAction):
    """
    Take the given information and attempt to remove all the downstream parameter information.
    """
    icon = qicons.delete
    title = "Clear broken parameter"
    parameter: Any

    def __init__(self, parameter: Union[Any, Callable], parent: QtCore.QObject):
        super().__init__(parent, parameter=parameter)

    def onTrigger(self, toggled):
        db = self.parameter.database
        code = self.parameter.code
        group = self.parameter.group

        # I'm not sure this is right, because you're removing all the exchanges from the group...
        parameters.remove_exchanges_from_group(group, None, False)
        ActivityParameter.delete().where((ActivityParameter.database == db) & (ActivityParameter.code == code)).execute()

        # Also clear Group if it is not in use anymore
        if not ActivityParameter.select().where(ActivityParameter.group == self.parameter.group).exists():
            Group.delete().where(Group.name == group).execute()
            GroupDependency.delete().where(GroupDependency.group == group).execute()
