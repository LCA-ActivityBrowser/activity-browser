# -*- coding: utf-8 -*-
import os

import brightway2 as bw
from PySide2 import QtWidgets

from ...bwutils import commontasks as bc


class DatabaseExportWizard(QtWidgets.QWizard):
    """ Present the user with a wizard that assist in either importing
    or exporting a database.
    On either import or exporting, present a progress bar
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Database export wizard")
        self.export_page = ExportDatabasePage(self)
        self.pages = [self.export_page]
        for i, page in enumerate(self.pages):
            self.setPage(i, page)
        self.show()

    def accept(self) -> None:
        self.perform_export()
        super().accept()

    def perform_export(self) -> None:
        db_name = self.field("database_choice")
        bc.store_database_as_package(db_name)


class ExportDatabasePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard = parent
        self.database = QtWidgets.QComboBox()
        self.database.currentIndexChanged.connect(self.changed)
        self.output_dir = QtWidgets.QLineEdit()
        self.output_dir.setReadOnly(True)
        self.complete = False

        box = QtWidgets.QGroupBox("Database selection:")
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Database:"), 0, 0, 1, 1)
        grid.addWidget(self.database, 0, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Exported databases are stored in the directory below:"), 1, 0, 1, 3)
        grid.addWidget(self.output_dir, 2, 0, 1, 3)
        box.setLayout(grid)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
        self.setLayout(layout)

        self.setFinalPage(True)
        self.registerField("database_choice", self.database, "currentText")

    def initializePage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.FinishButton, QtWidgets.QWizard.CancelButton]
        )
        self.database.clear()
        choices = ["-----"] + bw.databases.list
        self.database.addItems(choices)
        export_path = os.path.join(bw.projects.dir, "export")
        self.output_dir.setText(export_path)

    def changed(self):
        self.complete = False if self.database.currentText() == "-----" else True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete
