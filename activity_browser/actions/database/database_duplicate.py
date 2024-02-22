from typing import Union, Callable, Any

import brightway2 as bw
from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread
from activity_browser.controllers import database_controller


class DatabaseDuplicate(ABAction):
    icon = qicons.duplicate_database
    title = "Duplicate database..."
    tool_tip = "Make a duplicate of this database"
    db_name: str

    def __init__(self, database_name: Union[str, Callable], parent: QtCore.QObject):
        super().__init__(parent, db_name=database_name)

    def onTrigger(self, toggled):
        assert self.db_name in bw.databases

        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            f"Copy {self.db_name}",
            "Name of new database:" + " " * 25
        )
        if not new_name or not ok: return

        if new_name in bw.databases:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "A database with this name already exists."
            )
            return

        DuplicateDatabaseDialog(
            self.db_name,
            new_name,
            application.main_window
        )


class DuplicateDatabaseDialog(QtWidgets.QProgressDialog):
    def __init__(self, from_db: str, to_db: str, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Duplicating database')
        self.setLabelText(f'Duplicating existing database <b>{from_db}</b> to new database <b>{to_db}</b>:')
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
        database_controller.duplicate_database(self.copy_from, self.copy_to)

