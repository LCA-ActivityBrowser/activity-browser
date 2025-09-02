from typing import List

from qtpy import QtWidgets

import bw2data as bd
import bw_functional as bf

from bw2data.parameters import (ActivityParameter, Group,
                                                     GroupDependency,
                                                     parameters)

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ActivityDelete(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """

    icon = qicons.delete
    text = "Delete ***"

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        # retrieve activity objects from the controller using the provided keys
        activities = [bd.get_activity(key) for key in activity_keys]

        warnings = [f"Are you certain you want to delete {len(activities)} activity/activities?", ""]

        if any(len(act.upstream()) > 0 for act in activities):
            warnings.append("One or more of the activities you are trying to delete have consumers")

        if any([act for act in activities if isinstance(act, bf.Process)]):
            warnings.append("Products of processes will be removed as well")

        warning_text = "\n".join(warnings)

        # alert the user
        choice = QtWidgets.QMessageBox.warning(
            application.main_window,
            "Deleting activity/activities",
            warning_text,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        # return if the user cancels
        if choice == QtWidgets.QMessageBox.No:
            return

        for act in activities:
            db, code = act.key

            try:
                group_name = ActivityParameter.get(
                    (ActivityParameter.database == db)
                    & (ActivityParameter.code == code)
                ).group

                # remove activity parameters from its group
                parameters.remove_from_group(group_name, act)

                # Also clear the group if there are no more parameters in it
                if (
                    not ActivityParameter.select()
                    .where(ActivityParameter.group == group_name)
                    .exists()
                ):
                    Group.get(Group.name == group_name).delete_instance()
                    GroupDependency.delete().where(
                        GroupDependency.group == group_name
                    ).execute()
            except ActivityParameter.DoesNotExist:
                # no parameters found for this activity
                pass

            # Included in bw2data as of 4.1
            # act.upstream().delete()

            act.delete()
