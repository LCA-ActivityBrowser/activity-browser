# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from ...signals import signals


class CopyDatabaseDialog(QtWidgets.QProgressDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Copying database')
        self.setRange(0, 0)
        self.show()

        self.thread = CopyDatabaseThread(self)
        self.thread.finished.connect(self.finished)

    def begin_copy(self, copy_from: str, copy_to: str) -> None:
        if not all([copy_from, copy_to]):
            raise ValueError("Copy information not configured")
        if copy_from not in bw.databases:
            raise ValueError("Database <strong>{}</strong> does not exist!".format(copy_from))
        if copy_to in bw.databases:
            raise ValueError("Database <strong>{}</strong> already exists!".format(copy_to))
        self.setLabelText(
            'Copying existing database <b>{}</b> to new database <b>{}</b>:'.format(
                copy_from, copy_to)
        )
        self.thread.configure(copy_from, copy_to)
        self.thread.start()

    def finished(self, result: int = None) -> None:
        self.thread.exit(result or 0)
        self.setMaximum(1)
        self.setValue(1)
        signals.databases_changed.emit()


class CopyDatabaseThread(QtCore.QThread):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.copy_from = None
        self.copy_to = None

    def configure(self, copy_from: str, copy_to: str):
        self.copy_from = copy_from
        self.copy_to = copy_to

    def run(self):
        bw.Database(self.copy_from).copy(self.copy_to)
