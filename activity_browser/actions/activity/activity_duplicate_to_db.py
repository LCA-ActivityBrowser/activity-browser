from typing import List

from qtpy import QtWidgets

from activity_browser import application, settings
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import commontasks
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

from .activity_open import ActivityOpen


class ActivityDuplicateToDB(ABAction):
    """
    ABAction to duplicate an activity to another database. Asks the user to what database they want to copy the activity
    to, returns if there are no valid databases or when the user cancels. Otherwise uses the activity controller to
    duplicate the activities to the chosen database.
    """

    icon = qicons.duplicate_to_other_database
    text = "Duplicate to other database"

    @classmethod
    @exception_dialogs
    def run(cls, activity_keys: List[tuple], to_db: str = None):
        # from activity_browser.bwutils.metadata import AB_metadata
        activities = [bd.get_activity(key) for key in activity_keys]

        if to_db and not cls.confirm_db(to_db):
            return

        target_db = to_db or cls.request_db(activities)

        if not target_db:
            return

        new_activity_keys = []

        # otherwise move all supplied activities to the db using the controller
        for activity in activities:
            new_code = commontasks.generate_copy_code((target_db, activity["code"]))
            new_activity = activity.copy(code=new_code, database=target_db)
            new_activity_keys.append(new_activity.key)

        ActivityOpen.run(new_activity_keys)

    @staticmethod
    def request_db(activities):
        # get valid databases (not the original database, or locked databases)
        origin_db = next(iter(activities)).get("database")
        target_dbs = [
            db for db in settings.project_settings.get_editable_databases() if db != origin_db
        ]

        # return if there are no valid databases to duplicate to
        if not target_dbs:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only).",
            )
            return

        # construct a dialog where the user can choose a database to duplicate to
        target_db, ok = QtWidgets.QInputDialog.getItem(
            application.main_window,
            "Copy activity to database",
            "Target database:",
            target_dbs,
            0,
            False,
        )

        # return if the user didn't choose, or canceled
        if not ok:
            return

        return target_db

    @staticmethod
    def confirm_db(to_db: str):
        user_choice = QtWidgets.QMessageBox.question(
            application.main_window,
            "Duplicate to new database",
            f"Copy to {to_db} and open as new tab?",
        )
        return user_choice == user_choice.Yes
