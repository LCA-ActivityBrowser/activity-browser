import copy

from qtpy import QtWidgets

import bw2data as bd
import bw_functional as bf

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread

from .database_new import NewDatabaseDialog


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
        backend = bd.databases[db_name].get("backend", "undefined")

        if backend not in ["sqlite", "functional_sqlite"]:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                f"Unsupported database backend {backend}",
            )
            return

        name, backend, ok = NewDatabaseDialog.get_new_database_data(window_title="Duplicate database", backend=backend)

        if not name or not ok:
            return

        if name in bd.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "A database with this name already exists.",
            )
            return

        DuplicateDatabaseDialog(db_name, name, backend, application.main_window)


class DuplicateDatabaseDialog(QtWidgets.QProgressDialog):
    def __init__(self, from_db: str, to_db: str, backend: str, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Duplicating database")
        self.setLabelText(
            f"Duplicating existing database <b>{from_db}</b> to new database <b>{to_db}</b>:"
        )
        self.setModal(True)
        self.setRange(0, 0)

        self.dup_thread = DuplicateDatabaseThread(application)
        self.dup_thread.finished.connect(self.thread_finished)

        self.show()

        self.dup_thread.start(from_db, to_db, backend)

    def thread_finished(self) -> None:
        self.dup_thread.exit(0)
        self.setMaximum(1)
        self.setValue(1)


class DuplicateDatabaseThread(ABThread):

    def run_safely(self, copy_from, copy_to, backend):
        database = bd.Database(copy_from)

        data = database.load()
        data = database.relabel_data(data, copy_from, copy_to)

        new_database = bd.Database(copy_to, backend=backend)

        metadata = copy.copy(database.metadata)
        metadata["format"] = f"Copied from '{copy_from}'"
        metadata["backend"] = backend
        new_database.register(**metadata)

        if database.backend == "sqlite" and backend == "functional_sqlite":
            data = bf.convert_sqlite_to_functional_sqlite(data)
        elif database.backend == "functional_sqlite" and backend == "sqlite":
            data = bf.convert_functional_sqlite_to_sqlite(data)

        new_database.write(data, searchable=metadata.get("searchable"))
        return new_database
