from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.controllers.activity import activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction


class ActivityDelete(ABAction):
    icon = qicons.delete
    title = 'Delete ***'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        keys = self.activity_keys

        activities = activity_controller.get_activities(keys)

        text = ("One or more activities have downstream processes. "
                "Deleting these activities will remove the exchange from the downstream processes, this can't be undone.\n\n"
                "Are you sure you want to continue?")

        if any(len(act.upstream()) > 0 for act in activities):
            choice = QtWidgets.QMessageBox.warning(application.main_window,
                                                   "Activity/Activities has/have downstream processes",
                                                   text,
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
            if choice == QtWidgets.QMessageBox.No: return

        activity_controller.delete_activities(keys)