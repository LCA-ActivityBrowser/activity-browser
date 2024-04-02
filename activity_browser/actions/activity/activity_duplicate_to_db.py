from typing import Union, Callable, List

from PySide2 import QtWidgets, QtCore

from activity_browser import application, project_settings, activity_controller, activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction
from activity_browser.bwutils import commontasks


class ActivityDuplicateToDB(ABAction):
    """
    ABAction to duplicate an activity to another database. Asks the user to what database they want to copy the activity
    to, returns if there are no valid databases or when the user cancels. Otherwise uses the activity controller to
    duplicate the activities to the chosen database.
    """
    icon = qicons.duplicate_to_other_database
    title = 'Duplicate to other database'
    activity_keys: List[tuple]

    def __init__(self, activity_keys: Union[List[tuple], Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys)

    def onTrigger(self, toggled):
        # get bw activity objects from keys
        activities = [activity_controller.get(key) for key in self.activity_keys]

        # get valid databases (not the original database, or locked databases)
        origin_db = next(iter(activities)).get("database")
        target_dbs = [db for db in project_settings.get_editable_databases() if db != origin_db]

        # return if there are no valid databases to duplicate to
        if not target_dbs:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
            return

        # construct a dialog where the user can choose a database to duplicate to
        target_db, ok = QtWidgets.QInputDialog.getItem(
            application.main_window,
            "Copy activity to database",
            "Target database:",
            target_dbs,
            0,
            False
        )

        # return if the user didn't choose, or canceled
        if not target_db or not ok: return

        # otherwise move all supplied activities to the db using the controller
        for activity in activities:
            new_code = commontasks.generate_copy_code((target_db, activity["code"]))
            activity.copy(code=new_code, database=target_db)

