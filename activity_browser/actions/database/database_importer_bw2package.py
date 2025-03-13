import os
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, widgets, threading, composites
from activity_browser.bwutils.importers import ABPackage

log = getLogger(__name__)


class DatabaseImporterBW2Package(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = icons.qicons.import_db
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
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing Database")
        import_thread.finished.connect(progress_dialog.deleteLater)
        import_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None

    def __init__(self, database_name="", parent=None):
        super().__init__(parent)
        self.database_name = database_name

        self.setWindowTitle("Import database from Brightway2 Package")

        # Create db name textbox
        self.db_name_comp = composites.DatabaseNameComposite(
            label="Set database name:",
            database_preset=database_name,
        )
        self.db_name_comp.textChanged.connect(self.validate)

        # Create buttons
        self.buttons_comp = composites.HorizontalButtonsComposite("Cancel", "*OK")
        self.buttons_comp["Cancel"].clicked.connect(self.reject)
        self.buttons_comp["OK"].clicked.connect(self.accept)

        # Create layout and add widgets
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.db_name_comp)
        layout.addWidget(self.buttons_comp)

        # Set the dialog layout
        self.setLayout(layout)
        self.validate()

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = bool(self.db_name_comp.text)  # the textbox has been filled in

        self.buttons_comp["OK"].setEnabled(valid)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.db_name_comp.text
        super().accept()


class ImportPackageThread(threading.ABThread):
    path: str
    database_name: str

    def run_safely(self):
        ABPackage.import_file(self.path, rename=self.database_name)

