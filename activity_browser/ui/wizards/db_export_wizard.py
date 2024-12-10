# -*- coding: utf-8 -*-
import os

from qtpy import QtWidgets
from qtpy.QtCore import Slot

from activity_browser.bwutils import exporters as exp
from activity_browser.mod import bw2data as bd

EXPORTERS = {
    # Store data as a BW2Package.
    "BW2Package": exp.store_database_as_package,
    # Export the database, all project parameters and all parameters that are
    # related to that database as an Excel file.
    "Excel": exp.write_lci_excel,
}
EXTENSIONS = {
    "BW2Package": ".bw2package",
    "Excel": ".xlsx",
}


class DatabaseExportWizard(QtWidgets.QWizard):
    """Present the user with a wizard that assist in either importing
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

    def accept(self) -> None:
        self.perform_export()
        super().accept()

    def perform_export(self) -> None:
        db_name = self.field("database_choice")
        export_as = self.field("export_option")
        out_path = self.field("output_path")
        # Ensure that extension matches export_option.
        path, ext = os.path.splitext(out_path)
        if ext and not ext == EXTENSIONS[export_as]:
            ext = EXTENSIONS[export_as]
            out_path = path + ext
        elif not ext:
            out_path = path + EXTENSIONS[export_as]
        EXPORTERS[export_as](db_name, out_path)


class ExportDatabasePage(QtWidgets.QWizardPage):
    FILTERS = {
        "BW2Package": "BW2Package Files (*.bw2package);; All Files (*.*)",
        "Excel": "Excel Files (*.xlsx);; All Files (*.*)",
    }

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
        grid.addWidget(
            QtWidgets.QLabel("Exported data is stored in the directory below:"),
            2,
            0,
            1,
            3,
        )
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
            [
                QtWidgets.QWizard.Stretch,
                QtWidgets.QWizard.FinishButton,
                QtWidgets.QWizard.CancelButton,
            ]
        )
        self.database.clear()
        choices = ["-----"] + list(bd.databases)
        self.database.addItems(choices)
        self.output_dir.setText(str(bd.projects.output_dir))

    def changed(self):
        self.complete = False if self.database.currentText() == "-----" else True
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete

    @Slot(name="browseFile")
    def browse(self) -> None:
        file_filter = self.FILTERS[self.field("export_option")]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption="Save database", filter=file_filter
        )
        if path:
            self.output_dir.setText(path)
