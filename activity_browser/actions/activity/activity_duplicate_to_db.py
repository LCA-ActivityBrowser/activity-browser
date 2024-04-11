from typing import Union, Callable, List, Optional

from PySide2 import QtWidgets, QtCore

from activity_browser import application, project_settings, activity_controller
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction
from activity_browser.bwutils import commontasks

from .activity_open import ActivityOpen


class ActivityDuplicateToDB(ABAction):
    """
    ABAction to duplicate an activity to another database. Asks the user to what database they want to copy the activity
    to, returns if there are no valid databases or when the user cancels. Otherwise uses the activity controller to
    duplicate the activities to the chosen database.
    """
    icon = qicons.duplicate_to_other_database
    title = 'Duplicate to other database'
    activity_keys: List[tuple]
    to_db: str

    def __init__(self,
                 activity_keys: Union[List[tuple], Callable],
                 to_db: Optional[Union[str, Callable]],
                 parent: QtCore.QObject):
        super().__init__(parent, activity_keys=activity_keys, to_db=to_db)

    def onTrigger(self, toggled):
        # get bw activity objects from keys
        self.activities = [activity_controller.get(key) for key in self.activity_keys]

        if self.to_db and not self.confirm_db(): return

        target_db = self.to_db or self.request_db()

        if not target_db: return

        new_activity_keys = []
        # otherwise move all supplied activities to the db using the controller
        for activity in self.activities:
            new_code = commontasks.generate_copy_code((target_db, activity["code"]))
            new_activity = activity.copy(code=new_code, database=target_db)
            new_activity_keys.append(new_activity.key)

        ActivityOpen(new_activity_keys, None).trigger()



    def request_db(self):
        # get valid databases (not the original database, or locked databases)
        origin_db = next(iter(self.activities)).get("database")
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
        if not ok: return

        return target_db

    def confirm_db(self):
        user_choice = QtWidgets.QMessageBox.question(
            application.main_window,
            "Duplicate to new database",
            f"Copy to {self.to_db} and open as new tab?",
        )
        return user_choice == user_choice.Yes
