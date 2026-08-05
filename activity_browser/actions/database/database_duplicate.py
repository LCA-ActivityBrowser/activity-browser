from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.i18n import _
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread


class DatabaseDuplicate(ABAction):
    """
    ABAction to duplicate a database. Asks the user to provide a new name for the database, and returns when the name is
    already in use by an existing database. Then it shows a progress dialogue which will construct a new thread in which
    the database duplication will take place. This thread instructs the DatabaseController to duplicate the selected
    database with the chosen name.
    """

    icon = qicons.duplicate_database
    text = "Duplicate database..."
    tool_tip = "Make a duplicate of this database"

    @staticmethod
    @exception_dialogs
    def run(db_name: str):
        assert db_name in bd.databases

        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            _("Copy {database}", database=db_name),
            _("Name of new database:") + " " * 25,
        )
        if not new_name or not ok:
            return

        if new_name in bd.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                _("Not possible"),
                _("A database with this name already exists."),
            )
            return

        DuplicateDatabaseDialog(db_name, new_name, application.main_window)


class DuplicateDatabaseDialog(QtWidgets.QProgressDialog):
    def __init__(self, from_db: str, to_db: str, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(_("Duplicating database"))
        self.setLabelText(
            _(
                "Duplicating existing database <b>{source}</b> to new database "
                "<b>{target}</b>:",
                source=from_db,
                target=to_db,
            )
        )
        self.setModal(True)
        self.setRange(0, 0)

        self.thread = DuplicateDatabaseThread(from_db, to_db, self)
        self.thread.finished.connect(self.finished)

        self.show()

        self.thread.start()

    def finished(self, result: int = None) -> None:
        self.thread.exit(result or 0)
        self.setMaximum(1)
        self.setValue(1)


class DuplicateDatabaseThread(ABThread):
    def __init__(self, from_db, to_db, parent=None):
        super().__init__(parent=parent)
        self.copy_from = from_db
        self.copy_to = to_db

    def run_safely(self):
        database = bd.Database(self.copy_from)
        database.copy(self.copy_to)
