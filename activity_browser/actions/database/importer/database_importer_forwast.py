import os
import io
from logging import getLogger

import requests
import zipfile
import tempfile
from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, widgets, threading, composites
from activity_browser.bwutils.importers import ABPackage

log = getLogger(__name__)


class DatabaseImporterForwast(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = icons.qicons.import_db
    text = "Import database from Forwast"
    tool_tip = "Import database from Forwast"

    @classmethod
    @exception_dialogs
    def run(cls):
        # show the import setup dialog
        import_dialog = ImportSetupDialog(application.main_window)
        if import_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # initialize the import thread, setting needed attributes
        import_thread = ImportForwastThread(application)
        import_thread.database_name = import_dialog.database_name

        # setup a progress dialog
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing Forwast")
        import_thread.finished.connect(progress_dialog.deleteLater)
        import_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import database from Forwast")

        # Create db name textbox
        self.db_name_comp = composites.DatabaseNameComposite(
            label="Set database name:",
            database_preset="Forwast",
        )
        self.db_name_comp.database_name.textChanged.connect(self.validate)

        # Create buttons
        self.buttons = composites.HorizontalButtonsComposite("Cancel", "*OK")
        self.buttons["Cancel"].clicked.connect(self.reject)
        self.buttons["OK"].clicked.connect(self.accept)

        # Create layout and add widgets
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.db_name_comp)
        layout.addWidget(self.buttons)

        # Set the dialog layout
        self.setLayout(layout)
        self.validate()

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = bool(self.db_name_comp.database_name.text())  # the textbox has been filled in

        self.buttons["OK"].setEnabled(valid)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.db_name_comp.database_name.text()
        super().accept()


class ImportForwastThread(threading.ABThread):
    forwast_url = "https://lca-net.com/wp-content/uploads/forwast.bw2package.zip"
    database_name: str

    def run_safely(self):
        response = requests.get(self.forwast_url)
        forwast_zip = zipfile.ZipFile(io.BytesIO(response.content))
        with tempfile.TemporaryDirectory() as tempdir:
            forwast_zip.extractall(tempdir)
            path = os.path.join(tempdir, "forwast.bw2package")

            ABPackage.import_file(path, rename=self.database_name)

