from typing import Any

from activity_browser import signals
from activity_browser.actions.base import ABAction, exception_dialogs
from bw2data import get_activity
from bw2data.parameters import (ActivityParameter, Group,
                                                     GroupDependency,
                                                     parameters)
from activity_browser.ui.icons import qicons


class ParameterDelete(ABAction):
    """
    ABAction to delete an existing parameter.
    """

    icon = qicons.delete
    text = "Delete parameter..."

    @staticmethod
    @exception_dialogs
    def run(parameter: Any):
        if isinstance(parameter, ActivityParameter):
            db = parameter.database
            code = parameter.code
            amount = (
                ActivityParameter.select()
                .where(
                    (ActivityParameter.database == db)
                    & (ActivityParameter.code == code)
                )
                .count()
            )

            if amount > 1:
                parameter.delete_instance()
            else:
                group = parameter.group
                act = get_activity((db, code))
                parameters.remove_from_group(group, act)
                # Also clear the group if there are no more parameters in it

                if (
                    not ActivityParameter.select()
                    .where(ActivityParameter.group == group)
                    .exists()
                ):
                    Group.delete().where(Group.name == group).execute()
                    GroupDependency.delete().where(
                        GroupDependency.group == group
                    ).execute()
        else:
            parameter.delete_instance()
        # After deleting things, recalculate and signal changes
        parameters.recalculate()

        # No fire when everything is still fresh after recalculation, so need to fire manually to be sure everything is
        # updated correctly.
        signals.parameter.recalculated.emit()
