from typing import List

from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.parameters import ActivityParameter, Group, GroupDependency, parameters
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction, exception_dialogs


class ActivityDelete(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """
    icon = qicons.delete
    text = 'Delete ***'

    @staticmethod
    @exception_dialogs
    def run(activity_keys: List[tuple]):
        # retrieve activity objects from the controller using the provided keys
        activities = [bd.get_activity(key) for key in activity_keys]

        # check for downstream processes
        if any(len(act.upstream()) > 0 for act in activities):
            # warning text
            text = ("One or more activities have downstream processes. Deleting these activities will remove the "
                    "exchange from the downstream processes, this can't be undone.\n\nAre you sure you want to "
                    "continue?")

            # alert the user
            choice = QtWidgets.QMessageBox.warning(application.main_window,
                                                   "Activity/Activities has/have downstream processes",
                                                   text,
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)

            # return if the user cancels
            if choice == QtWidgets.QMessageBox.No: return

        # use the activity controller to delete multiple activities
        for act in activities:
            db, code = act.key

            try:
                group_name = ActivityParameter.get(
                    (ActivityParameter.database == db) & (ActivityParameter.code == code)).group

                # remove activity parameters from its group
                parameters.remove_from_group(group_name, act)

                # Also clear the group if there are no more parameters in it
                if not ActivityParameter.select().where(ActivityParameter.group == group_name).exists():
                    Group.delete().where(Group.name == group_name).execute()
                    GroupDependency.delete().where(GroupDependency.group == group_name).execute()
            except ActivityParameter.DoesNotExist:
                # no parameters found for this activity
                pass

            act.upstream().delete()

            act.delete()
