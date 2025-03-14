from logging import getLogger

from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import threading, widgets
from activity_browser.bwutils.importers import ABExcelImporter

log = getLogger(__name__)


class DatabaseImporterExcel(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    text = "Import database from brightway excel format"
    tool_tip = "Import database from brightway excel format"

    @classmethod
    @exception_dialogs
    def run(cls):
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose brightway excel database to import',
            filter='excel spreadsheet (*.xlsx);; All files (*.*)'
        )
        if not path:
            return

        import_setup = ImportSetup(title="Import from Excel", context={"path": path})
        import_setup.exec_()


class ImportSetup(widgets.ABWizard):

    class ExtractPage(widgets.ABThreadedWizardPage):
        title = "Extracting Database"
        subtitle = "Extracting database from excel file"

        class Thread(threading.ABThread):
            loaded: SignalInstance = Signal(object)

            def run_safely(self, path: str):
                importer = ABExcelImporter(path)
                self.loaded.emit(importer)

        def initializePage(self, context: dict):
            """Start the download thread"""
            def set_importer(importer):
                context.__setitem__("importer", importer)

            self.thread.start(context["path"])
            self.thread.loaded.connect(lambda i: context.__setitem__("importer", i))

        def nextPage(self) -> type[QtWidgets.QWizardPage] | None:
            return ImportSetup.DatabaseName

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
            self.db_name_edit.setText(context["importer"].db_name)

        def finalize(self, context: dict):
            context["database_name"] = self.db_name_edit.text()

        def nextPage(self):
            return ImportSetup.InstallPage

    class InstallPage(widgets.ABThreadedWizardPage):
        title = "Importing Database"
        subtitle = "Importing database from .bw2package file"

        class Thread(threading.ABThread):
            """Thread to handle the install process"""

            def run_safely(self, importer: ABExcelImporter, database_name: str, linking_dict: dict):
                """Download the ecoinvent release"""
                importer.automated_import(database_name, linking_dict)

        def initializePage(self, context: dict):
            """Start the download thread"""
            self.thread.start(context["importer"], context["database_name"], {})

    pages = [ExtractPage, DatabaseName, InstallPage]
