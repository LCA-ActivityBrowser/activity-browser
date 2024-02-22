from typing import Union, Callable, List

import brightway2 as bw
from PySide2 import QtWidgets, QtCore

from activity_browser import signals, application
from activity_browser.bwutils.strategies import relink_activity_exchanges
from activity_browser.actions.base import ABAction
from activity_browser.ui.widgets import ActivityLinkingDialog, ActivityLinkingResultsDialog
from activity_browser.ui.icons import qicons


class ActivityRelink(ABAction):
    icon = qicons.edit
    title = "Relink the activity exchanges"
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        key = self.activity_keys[0]

        db = bw.Database(key[0])
        activity = db.get(key[1])

        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]

        dialog = ActivityLinkingDialog.relink_sqlite(
            activity['name'],
            options,
            application.main_window
        )

        if dialog.exec_() == ActivityLinkingDialog.Rejected: return

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        relinking_results = {}
        for old, new in dialog.relink.items():
            other = bw.Database(new)
            failed, succeeded, examples = relink_activity_exchanges(activity, old, other)
            relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)

        QtWidgets.QApplication.restoreOverrideCursor()

        if failed > 0:
            relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(
                application.main_window,
                relinking_results,
                examples
            )
            relinking_dialog.exec_()
            activity = relinking_dialog.open_activity()

        signals.database_changed.emit(activity['name'])
        signals.databases_changed.emit()
