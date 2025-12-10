from typing import Any

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from bw2data import get_activity
from bw2data.parameters import (ActivityParameter, Group,
                                                     GroupDependency,
                                                     parameters)
from activity_browser.ui.icons import qicons
from activity_browser.bwutils.utils import Parameter


class ParameterGroupDelete(ABAction):
    """
    ABAction to delete an existing parameter.
    """

    icon = qicons.delete
    text = "Delete parameter group..."

    @staticmethod
    @exception_dialogs
    def run(parameter_groups: list[str]):
        for group in parameter_groups:
            group_entry = Group.get(Group.name == group)

            # Delete all parameters in the group
            params_in_group = ActivityParameter.select().where(ActivityParameter.group == group)
            if any([ActivityParameter.is_dependent_on(p.name, p.group) for p in params_in_group]):
                raise Exception(f"Cannot delete parameter group '{group}' because some parameters are dependencies for other parameters.")

            for param in params_in_group:
                param.delete_instance()

            # Delete group dependencies
            GroupDependency.delete().where(GroupDependency.group == group).execute()
            # Delete the group itself
            group_entry.delete_instance()


        # After deleting things, recalculate and signal changes
        parameters.recalculate()

        # No fire when everything is still fresh after recalculation, so need to fire manually to be sure everything is
        # updated correctly.
        app.signals.parameter.recalculated.emit()
