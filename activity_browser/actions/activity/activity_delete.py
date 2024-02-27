from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import application, activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityDelete(ABAction):
    """
    ABAction to delete one or multiple activities if supplied by activity keys. Will check if an activity has any
    downstream processes and ask the user whether they want to continue if so. Exchanges from any downstream processes
    will be removed
    """
    icon = qicons.delete
    title = 'Delete ***'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        # retrieve activity objects from the controller using the provided keys
        activities = activity_controller.get_activities(self.activity_keys)

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
        activity_controller.delete_activities(self.activity_keys)
