# -*- coding: utf-8 -*-
import os

import brightway2 as bw
from PySide2 import QtWidgets

from ...bwutils import commontasks as bc
from ...signals import signals


class DatabaseTransferWizard(QtWidgets.QWizard):
    """ Present the user with a wizard that assist in either importing
    or exporting a database.

    On either import or exporting, present a progress bar
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Database import/export wizard")
        self.transfer_page = TransferTypePage(self)
        self.import_page = ImportDatabasePage(self)
        self.export_page = ExportDatabasePage(self)
        self.pages = [
            self.transfer_page,
            self.import_page,
            self.export_page
        ]
        for i, page in enumerate(self.pages):
            self.setPage(i, page)
        self.show()

    def accept(self) -> None:
        if self.field("import") is True:
            self.perform_import()
        else:
            self.perform_export()
        super().accept()

    def perform_import(self) -> None:
        path = self.field("import_path")
        name = self.field("alternate_name")
        (_, success) = bc.import_database_from_package(path, name)
        if success:
            # If success: emit new db signal
            signals.databases_changed.emit()

    def perform_export(self) -> None:
        db_name = self.field("database_choice")
        bc.store_database_as_package(db_name)


class TransferTypePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard = parent
        self.import_btn = QtWidgets.QRadioButton("Import database from file")
        self.export_btn = QtWidgets.QRadioButton("Export local database to file")
        option_box = QtWidgets.QGroupBox("Import or export database:")
        box_layout = QtWidgets.QVBoxLayout()
        box_layout.addWidget(self.import_btn)
        box_layout.addWidget(self.export_btn)
        self.import_btn.setChecked(True)
        option_box.setLayout(box_layout)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(option_box)
        self.setLayout(layout)

        self.registerField("import", self.import_btn)
        self.registerField("export", self.export_btn)

    def nextId(self) -> int:
        if self.field("import"):
            return 1
        elif self.field("export"):
            return 2


class ImportDatabasePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard = parent
        self.path = QtWidgets.QLineEdit()
        self.path.setReadOnly(True)
        self.path.textChanged.connect(self.changed)
        self.path_btn = QtWidgets.QPushButton("Browse")
        self.path_btn.clicked.connect(self.browse)
        self.alt_name = QtWidgets.QLineEdit()
        self.complete = False

        option_box = QtWidgets.QGroupBox("Import path and database name:")
        grid_layout = QtWidgets.QGridLayout()
        layout = QtWidgets.QVBoxLayout()
        grid_layout.addWidget(QtWidgets.QLabel("Path to file*"), 0, 0, 1, 1)
        grid_layout.addWidget(self.path, 0, 1, 1, 2)
        grid_layout.addWidget(self.path_btn, 0, 3, 1, 1)
        grid_layout.addWidget(QtWidgets.QLabel("Alternate database name"), 1, 0, 1, 1)
        grid_layout.addWidget(self.alt_name, 1, 1, 1, 2)
        option_box.setLayout(grid_layout)
        layout.addWidget(option_box)
        self.setLayout(layout)

        self.setFinalPage(True)
        self.registerField("import_path*", self.path)
        self.registerField("alternate_name", self.alt_name)

    def initializePage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.BackButton, QtWidgets.QWizard.Stretch,
             QtWidgets.QWizard.FinishButton, QtWidgets.QWizard.CancelButton]
        )
        self.path.clear()
        self.alt_name.clear()

    def cleanupPage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.NextButton, QtWidgets.QWizard.CancelButton]
        )

    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self, caption="Select a valid BW2Package file"
        )
        if path:
            self.path.setText(path)

    def changed(self):
        self.complete = True if os.path.isfile(self.path.text()) else False
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete


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
            [QtWidgets.QWizard.BackButton, QtWidgets.QWizard.Stretch,
             QtWidgets.QWizard.FinishButton, QtWidgets.QWizard.CancelButton]
        )
        self.database.clear()
        choices = ["-----"] + bw.databases.list
        self.database.addItems(choices)
        export_path = os.path.join(bw.projects.dir, "export")
        self.output_dir.setText(export_path)

    def cleanupPage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.NextButton, QtWidgets.QWizard.CancelButton]
        )

    def changed(self):
        self.complete = False if self.database.currentText() == "-----" else True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete
