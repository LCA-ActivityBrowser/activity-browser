import os
from logging import getLogger

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread
from activity_browser.ui.widgets import ABProgressDialog
from activity_browser.bwutils.importers import ABPackage

log = getLogger(__name__)


class DatabaseImporterBW2Package(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from .bw2package"
    tool_tip = "Import database from .bw2package"

    @classmethod
    @exception_dialogs
    def run(cls):
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose .bw2package to import',
            filter='Brightway2 Database Package (*.bw2package);; All files (*.*)'
        )
        if not path:
            return

        # a bit of pathname magic to get a suggested database name
        filename = os.path.basename(path).split('.bw2package')[0]

        # show the import setup dialog
        import_dialog = ImportSetupDialog(filename, application.main_window)
        if import_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # initialize the import thread, setting needed attributes
        import_thread = ImportPackageThread(application)
        import_thread.path = path
        import_thread.database_name = import_dialog.database_name

        # setup a progress dialog
        progress_dialog = ABProgressDialog.get_connected_dialog("Importing Database")
        import_thread.finished.connect(progress_dialog.deleteLater)
        import_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None

    def __init__(self, database_name="", parent=None):
        super().__init__(parent)
        self.database_name = database_name

        self.setWindowTitle("Import database from Brightway2 Package")

        # Create db name textbox
        self.db_name_textbox = QtWidgets.QLineEdit()
        self.db_name_textbox.setPlaceholderText("Database name")
        self.db_name_textbox.setText(self.database_name)
        self.db_name_textbox.textChanged.connect(self.db_name_check)

        # Create warning text for when the user enters a database that already exists
        self.db_name_warning = QtWidgets.QLabel()
        self.db_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.db_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing database will be overwritten</p>")
        self.db_name_warning.setHidden(True)

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
        layout.addLayout(button_layout)

        # Set the dialog layout
        self.setLayout(layout)
        self.validate()

    def db_name_check(self):
        """Slot for when the db_name_textbox is changed, hide/show the warning and validate"""
        if self.db_name_textbox.text() in bd.databases:
            self.db_name_warning.setHidden(False)
        else:
            self.db_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = bool(self.db_name_textbox.text())  # the textbox has been filled in

        self.ok_button.setEnabled(valid)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.db_name_textbox.text()
        super().accept()


class ImportPackageThread(ABThread):
    path: str
    database_name: str

    def run_safely(self):
        ABPackage.import_file(self.path, rename=self.database_name)

