from typing import Union, Callable, Any

import brightway2 as bw
from PySide2 import QtWidgets, QtCore

from activity_browser import application, signals
from .base import ABAction
from ..ui.icons import qicons
from ..ui.widgets import DatabaseLinkingDialog, DatabaseLinkingResultsDialog
from ..bwutils.strategies import relink_exchanges_existing_db
from ..controllers import database_controller


class DatabaseRelink(ABAction):
    icon = qicons.edit
    title = "Relink the database"
    tool_tip = "Relink the dependencies of this database"
    db_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, db_name=database_name)

    def onTrigger(self, toggled):
        db = bw.Database(self.db_name)
        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]
        dialog = DatabaseLinkingDialog.relink_sqlite(self.db_name, options, application.main_window)
        relinking_results = dict()
        if dialog.exec_() == DatabaseLinkingDialog.Accepted:
            # Now, start relinking.
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                failed, succeeded, examples = relink_exchanges_existing_db(db, old, other)
                relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)
            QtWidgets.QApplication.restoreOverrideCursor()
            if failed > 0:
                QtWidgets.QApplication.restoreOverrideCursor()
                relinking_dialog = DatabaseLinkingResultsDialog.present_relinking_results(application.main_window,
                                                                                          relinking_results, examples)
                relinking_dialog.exec_()
                activity = relinking_dialog.open_activity()
            QtWidgets.QApplication.restoreOverrideCursor()
            signals.database_changed.emit(self.db_name)
            signals.databases_changed.emit()

