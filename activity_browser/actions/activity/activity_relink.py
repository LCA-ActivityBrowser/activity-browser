from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import signals, application, database_controller
from activity_browser.bwutils.strategies import relink_activity_exchanges
from activity_browser.actions.base import ABAction
from activity_browser.ui.widgets import ActivityLinkingDialog, ActivityLinkingResultsDialog
from activity_browser.ui.icons import qicons


class ActivityRelink(ABAction):
    """
    ABAction to relink the exchanges of an activity to exchanges from another database.

    This action only uses the first key from activity_keys
    """
    icon = qicons.edit
    title = "Relink the activity exchanges"
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        # this action only uses the first key supplied to activity_keys
        key = self.activity_keys[0]

        # extract the brightway database and activity
        db = database_controller.get(key[0])
        activity = db.get(key[1])

        # find the dependents for the database and construct the alternatives in tuple format
        depends = db.find_dependents()
        options = [(depend, list(database_controller)) for depend in depends]

        # present the alternatives to the user in a linking dialog
        dialog = ActivityLinkingDialog.relink_sqlite(
            activity['name'],
            options,
            application.main_window
        )

        # return if the user cancels
        if dialog.exec_() == ActivityLinkingDialog.Rejected: return

        # relinking will take some time, set WaitCursor
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # use the relink_activity_exchanges strategy to relink the exchanges of the activity
        relinking_results = {}
        for old, new in dialog.relink.items():
            other = database_controller.get(new)
            failed, succeeded, examples = relink_activity_exchanges(activity, old, other)
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        # restore normal cursor
        QtWidgets.QApplication.restoreOverrideCursor()

        # if any relinks failed present them to the user
        if failed > 0:
            relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(
                application.main_window,
                relinking_results,
                examples
            )
            relinking_dialog.exec_()
