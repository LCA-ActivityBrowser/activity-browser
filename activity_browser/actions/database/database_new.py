from PySide2 import QtWidgets

from activity_browser import application, project_settings, signals
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class DatabaseNew(ABAction):
    """
    ABAction to create a new database. First asks the user to provide a name for the new database. Returns if the user
    cancels, or when an existing database already has the chosen name. Otherwise, instructs the controller to create a
    new database with the chosen name.
    """
    icon = qicons.add
    text = "New database..."
    tool_tip = "Make a new database"

    @staticmethod
    @exception_dialogs
    def run():
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new database",
            "Name of new database:" + " " * 25
        )

        if not ok or not name: return

        if name in bd.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "A database with this name already exists."
            )
            return

        db = bd.Database(name)
        db.register()
        project_settings.add_db(name, False)

        signals.database_selected.emit(name)
