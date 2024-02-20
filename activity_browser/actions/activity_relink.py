import brightway2 as bw
from PySide2.QtCore import Qt
from PySide2 import QtWidgets

from activity_browser import signals, application
from activity_browser.bwutils.strategies import relink_activity_exchanges
from .base import ABAction
from ..ui.widgets import ActivityLinkingDialog, ActivityLinkingResultsDialog
from ..ui.icons import qicons


class ActivityRelink(ABAction):
    icon = qicons.edit
    title = "Relink the activity exchanges"
    depends = ["selected_keys"]

    def onTrigger(self, toggled):
        keys = self.parent().selected_keys
        key = keys[0]

        db = bw.Database(key[0])
        activity = db.get(key[1])

        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]
        dialog = ActivityLinkingDialog.relink_sqlite(activity['name'], options, application.main_window)
        relinking_results = {}
        if dialog.exec_() == ActivityLinkingDialog.Accepted:
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                failed, succeeded, examples = relink_activity_exchanges(activity, old, other)
                relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)
            QtWidgets.QApplication.restoreOverrideCursor()
            if failed > 0:
                relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(application.main_window,
                                                                                          relinking_results, examples)
                relinking_dialog.exec_()
                activity = relinking_dialog.open_activity()
            signals.database_changed.emit(activity['name'])
            signals.databases_changed.emit()
