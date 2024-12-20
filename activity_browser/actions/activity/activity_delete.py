from typing import List

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from bw2data.parameters import (ActivityParameter, Group,
                                                     GroupDependency,
                                                     parameters)
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

        warning_text = f"Are you certain you want to delete {len(activities)} activity/activities?"

        # check for downstream processes
        if any(len(act.upstream()) > 0 for act in activities):
            # warning text
            warning_text += (
                "\n\nOne or more activities have downstream processes. Deleting these activities will remove the "
                "exchange from the downstream processes as well."
            )

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



        # use the activity controller to delete multiple activities
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
