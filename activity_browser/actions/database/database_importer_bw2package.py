import os
from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, widgets, threading
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
        context = {
            "path": path,
            "database_name": os.path.basename(path).split('.bw2package')[0]
        }

        # show the import setup dialog
        import_dialog = ImportSetup(parent=application.main_window, title="Import Database", context=context)
        import_dialog.exec_()


class ImportSetup(widgets.ABWizard):
    class DatabaseName(widgets.ABWizardPage):
        title = "Database Name"
        subtitle = "Enter the name of the database you wish to create"

        def __init__(self, parent=None):
            super().__init__(parent)
            self.db_name_edit = widgets.DatabaseNameEdit(
                label="Set database name:",
                database_preset="",
            )
            self.db_name_edit.textChanged.connect(self.completeChanged)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.db_name_edit)
            self.setLayout(layout)

        def isComplete(self):
            return bool(self.db_name_edit.text())

        def initializePage(self, context: dict):
            self.db_name_edit.setText(context["database_name"])

        def finalize(self, context: dict):
            context["database_name"] = self.db_name_edit.text()

        def nextPage(self):
            return ImportSetup.InstallPage

    class InstallPage(widgets.ABThreadedWizardPage):
        """Wizard page to install the selected bw2package"""
        title = "Importing Database"
        subtitle = "Importing database from .bw2package file"

        class Thread(threading.ABThread):
            """Thread to handle the install process"""
            def run_safely(self, path: str, db_name: str):
                """Download the ecoinvent release"""
                ABPackage.import_file(path, rename=db_name)

        def initializePage(self, context: dict):
            """Start the download thread"""
            self.thread.start(context["path"], context["database_name"])

    pages = [DatabaseName, InstallPage]

