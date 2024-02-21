from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import application, project_settings
from ..controllers.activity import activity_controller
from ..ui.icons import qicons
from .base import ABAction


class ActivityDuplicateToDB(ABAction):
    icon = qicons.duplicate_to_other_database
    title = 'Duplicate to other database'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        activities = activity_controller.get_activities(self.activity_keys)
        origin_db = next(iter(activities)).get("database")
        target_dbs = [db for db in project_settings.get_editable_databases() if db != origin_db]

        if not target_dbs:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
            return

        target_db, ok = QtWidgets.QInputDialog.getItem(
            application.main_window,
            "Copy activity to database",
            "Target database:",
            target_dbs,
            0,
            False
        )

        if not target_db or not ok: return

        for activity in activities:
            activity_controller.duplicate_activity_to_db(target_db, activity)

