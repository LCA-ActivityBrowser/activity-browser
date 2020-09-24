# -*- coding: utf-8 -*-
import os

import brightway2 as bw
from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from ...bwutils import commontasks as bc
from ...bwutils.exporters import write_lci_excel


EXPORTERS = {
    # Store data as a BW2Package.
    "BW2Package": bc.store_database_as_package,
    # Export the database, all project parameters and all parameters that are
    # related to that database as an Excel file.
    "Excel": write_lci_excel,
}


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
        export_as = self.field("export_option")
        out_path = self.field("output_path")
        EXPORTERS[export_as](db_name, out_path)


class ExportDatabasePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard = parent
        self.database = QtWidgets.QComboBox()
        self.export_option = QtWidgets.QComboBox()
        self.export_option.addItems(list(EXPORTERS))
        self.database.currentIndexChanged.connect(self.changed)
        self.output_dir = QtWidgets.QLineEdit()
        self.output_dir.setReadOnly(True)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse)
        self.complete = False

        box = QtWidgets.QGroupBox("Database selection:")
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Database:"), 0, 0, 1, 1)
        grid.addWidget(self.database, 0, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Exported as:"), 1, 0, 1, 1)
        grid.addWidget(self.export_option, 1, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Exported data is stored in the directory below:"), 2, 0, 1, 3)
        grid.addWidget(self.output_dir, 3, 0, 1, 2)
        grid.addWidget(self.browse_button, 3, 2, 1, 1)
        box.setLayout(grid)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
        self.setLayout(layout)

        self.setFinalPage(True)
        self.registerField("database_choice", self.database, "currentText")
        self.registerField("export_option", self.export_option, "currentText")
        self.registerField("output_path*", self.output_dir)

    def initializePage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.FinishButton, QtWidgets.QWizard.CancelButton]
        )
        self.database.clear()
        choices = ["-----"] + bw.databases.list
        self.database.addItems(choices)
        self.output_dir.setText(bw.projects.output_dir)

    def changed(self):
        self.complete = False if self.database.currentText() == "-----" else True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete

    @Slot(name="browseFile")
    def browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption="Save database",
            filter="Database Files (*.xlsx *.bw2package);; All Files (*.*)"
        )
        if path:
            self.output_dir.setText(path)
