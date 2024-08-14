import sys

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter


class DatabaseImporterEcoinvent7z(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from ecoinvent .7z file"
    tool_tip = "Import database from ecoinvent .7z file"

    @staticmethod
    @exception_dialogs
    def run():
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose ecoinvent .7z file to import',
            filter='7z archive (*.7z);; All files (*.*)'
        )
        if not path:
            return

        importer = Ecoinvent7zImporter(path)

        setup_dialog = ImportSetupDialog()
        if setup_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        if setup_dialog.import_biosphere:
            importer.install_biosphere(setup_dialog.biosphere_name)

        importer.install_ecoinvent(setup_dialog.database_name, setup_dialog.biosphere_name)


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None
    biosphere_name = None
    import_biosphere = False
    
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create db name textbox
        self.db_name_textbox = QtWidgets.QLineEdit()
        self.db_name_textbox.setPlaceholderText("Database name")
        self.db_name_textbox.textChanged.connect(self.db_name_check)

        self.db_name_warning = QtWidgets.QLabel()
        self.db_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.db_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing database will be overwritten</p>")
        self.db_name_warning.setHidden(True)

        # Create biosphere choice buttons
        self.existing_bio_radio = QtWidgets.QRadioButton("Link to an existing biosphere")
        self.import_bio_radio = QtWidgets.QRadioButton("Import bundled biosphere")

        self.existing_bio_radio.clicked.connect(self.select_existing_bio)
        self.import_bio_radio.clicked.connect(self.select_import_bio)

        # Add radio buttons to a button group
        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(self.existing_bio_radio, id=1)
        self.button_group.addButton(self.import_bio_radio, id=2)

        # Drop-down for an existing biosphere
        self.bio_name_dropdown = QtWidgets.QComboBox(self)
        self.bio_name_dropdown.addItems(bd.databases)
        self.bio_name_dropdown.setHidden(True)

        # Text-box for bundled biosphere
        self.bio_name_textbox = QtWidgets.QLineEdit()
        self.bio_name_textbox.setPlaceholderText("New biosphere name")
        self.bio_name_textbox.setHidden(True)
        self.bio_name_textbox.textChanged.connect(self.bio_name_check)

        self.bio_name_warning = QtWidgets.QLabel()
        self.bio_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.bio_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing biosphere will be overwritten</p>")
        self.bio_name_warning.setHidden(True)

        # Create OK and Cancel buttons
        self.ok_button = QtWidgets.QPushButton("OK")
        self.cancel_button = QtWidgets.QPushButton("Cancel")

        self.ok_button.setEnabled(False)

        # Connect buttons to their respective slots
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Set button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        # Create layout and add widgets
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel("Set database name:"))
        layout.addWidget(self.db_name_textbox)
        layout.addWidget(self.db_name_warning)
        layout.addWidget(self.existing_bio_radio)
        layout.addWidget(self.bio_name_dropdown)
        layout.addWidget(self.import_bio_radio)
        layout.addWidget(self.bio_name_textbox)
        layout.addWidget(self.bio_name_warning)
        layout.addLayout(button_layout)

        # Set the dialog layout
        self.setLayout(layout)

    def select_existing_bio(self):
        self.bio_name_textbox.setHidden(True)
        self.bio_name_dropdown.setHidden(False)
        self.validate()

    def select_import_bio(self):
        self.bio_name_dropdown.setHidden(True)
        self.bio_name_textbox.setHidden(False)
        self.validate()

    def db_name_check(self):
        if self.db_name_textbox.text() in bd.databases:
            self.db_name_warning.setHidden(False)
        else:
            self.db_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def bio_name_check(self):
        if self.bio_name_textbox.text() in bd.databases:
            self.bio_name_warning.setHidden(False)
        else:
            self.bio_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def validate(self):
        valid = (
            bool(self.db_name_textbox.text()) and (
                self.existing_bio_radio.isChecked() or (
                    self.import_bio_radio.isChecked() and
                    bool(self.bio_name_textbox.text())
                )
            )
        )
        self.ok_button.setEnabled(valid)
    
    def accept(self):
        self.database_name = self.db_name_textbox.text()
        if self.import_bio_radio.isChecked():
            self.import_biosphere = True
            self.biosphere_name = self.bio_name_textbox.text()
        else:
            self.biosphere_name = self.bio_name_dropdown.currentText()
        super().accept()
        
