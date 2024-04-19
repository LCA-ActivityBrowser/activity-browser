from typing import Union, Callable, Any

from PySide2 import QtCore

from activity_browser.brightway.bw2data import get_activity
from activity_browser.brightway.bw2data.parameters import ActivityParameter, Group, parameters
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
        with parameters.db.atomic() as txn:
            parameters.remove_exchanges_from_group(self.parameter.group, None, False)
            ActivityParameter.delete().where(
                ActivityParameter.database == self.parameter.database,
                ActivityParameter.code == self.parameter.code
            ).execute()
            # Do commit to ensure .exists() call does not include deleted params
            txn.commit()
            exists = (ActivityParameter.select()
                      .where(ActivityParameter.group == self.parameter.group)
                      .exists())
            if not exists:
                # Also clear Group if it is not in use anymore
                Group.delete().where(Group.name == self.parameter.group).execute()
