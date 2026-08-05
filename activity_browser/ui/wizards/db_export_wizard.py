# -*- coding: utf-8 -*-
import os

from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from activity_browser.bwutils import exporters as exp
from activity_browser.i18n import _
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
        self.setWindowTitle(_("Database export wizard"))
        self.export_page = ExportDatabasePage(self)
        self.pages = [self.export_page]
        for i, page in enumerate(self.pages):
            self.setPage(i, page)

    def accept(self) -> None:
        self.perform_export()
        super().accept()

    def perform_export(self) -> None:
        db_name = self.field("database_choice")
        export_as = self.export_page.selected_exporter
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
        self.setTitle(_("Export database"))
        self.wizard = parent
        self.database = QtWidgets.QComboBox()
        self.export_option = QtWidgets.QComboBox()
        for exporter_id in EXPORTERS:
            self.export_option.addItem(exporter_id, exporter_id)
        self.database.currentIndexChanged.connect(self.changed)
        self.output_dir = QtWidgets.QLineEdit()
        self.output_dir.setReadOnly(True)
        self.browse_button = QtWidgets.QPushButton(_("Browse"))
        self.browse_button.clicked.connect(self.browse)
        self.complete = False

        box = QtWidgets.QGroupBox(_("Database selection:"))
        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(_("Database:")), 0, 0, 1, 1)
        grid.addWidget(self.database, 0, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel(_("Exported as:")), 1, 0, 1, 1)
        grid.addWidget(self.export_option, 1, 1, 1, 2)
        grid.addWidget(
            QtWidgets.QLabel(_("Exported data is stored in the directory below:")),
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
        self.registerField("export_option", self.export_option, "currentIndex")
        self.registerField("output_path*", self.output_dir)

    @property
    def selected_exporter(self) -> str:
        """Return the stable exporter ID stored separately from its label."""

        return self.export_option.currentData()

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
        self.output_dir.setText(bd.projects.output_dir)

    def changed(self):
        self.complete = self.database.currentIndex() > 0
        self.completeChanged.emit()

    def isComplete(self):
        return self.complete

    @Slot(name="browseFile")
    def browse(self) -> None:
        file_filter = _(self.FILTERS[self.selected_exporter])
        path = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption=_("Save database"), filter=file_filter
        )[0]
        if path:
            self.output_dir.setText(path)
