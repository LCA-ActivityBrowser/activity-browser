from loguru import logger

from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui import widgets
from activity_browser.bwutils.importers import ABExcelImporter
from activity_browser.bwutils.metadata.loader import schedule_database_metadata_reload
from activity_browser.ui.core import threading




class DatabaseImporterExcel(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    text = "Import database from brightway excel format"
    tool_tip = "Import database from brightway excel format"

    @classmethod
    @exception_dialogs
    def run(cls):
        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=app.main_window,
            caption='Choose brightway excel database to import',
            filter='excel spreadsheet (*.xlsx);; All files (*.*)'
        )
        if not path:
            return

        import_setup = ImportSetup(title="Import from Excel", context={"path": path})
        import_setup.exec_()


class ImportSetup(widgets.ABWizard):

    def customButtonOne(self):
        def callback():
            importer : ABExcelImporter = self.context.get("importer")
            if not importer:
                return
            dialog = app.dialogs.ImportPreviewDialog(importer, parent=app.main_window)
            dialog.exec_()
        return "Data", callback

    class ExtractPage(widgets.ABThreadedWizardPage):
        title = "Extracting Database"
        subtitle = "Extracting database from excel file"
        buttonLayout = ["CustomButton1", "Stretch", "CancelButton", "NextButton"]
        customButton1Text = "Show extracted data"

        class Thread(threading.ABThread):
            loaded: SignalInstance = Signal(object)

            def run_safely(self, path: str):
                importer = ABExcelImporter(path)
                importer.apply_basic_strategies()
                self.loaded.emit(importer)

        def initializePage(self, context: dict):
            """Start the download thread"""
            self.thread.start(context["path"])
            self.thread.loaded.connect(self.thread_finished)

            button = self.wizard().button(QtWidgets.QWizard.CustomButton1)
            button.setEnabled(False)

        def thread_finished(self, importer: ABExcelImporter):
            logger.debug("Extraction thread finished")
            self.context()["importer"] = importer

            button = self.wizard().button(QtWidgets.QWizard.CustomButton1)
            button.setEnabled(True)

        def nextPage(self) -> type[QtWidgets.QWizardPage] | None:
            return ImportSetup.DatabaseName

    class DatabaseName(widgets.ABWizardPage):
        title = "Database Name"
        subtitle = "Enter the name of the database you wish to create"
        buttonLayout = ["CustomButton1", "Stretch", "CancelButton", "NextButton"]

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
            self.wizard().setButtonText(QtWidgets.QWizard.WizardButton.NextButton, "Apply")

        def finalize(self, context: dict):
            importer = context["importer"]
            importer.apply_db_name(self.db_name_edit.text())

            context["database_name"] = self.db_name_edit.text()

        def nextPage(self):
            return ImportSetup.DatabaseLink

    class DatabaseLink(widgets.ABWizardPage):
        title = "Link Databases"
        subtitle = "Link the imported database to existing databases"
        buttonLayout = ["CustomButton1", "Stretch", "CancelButton", "NextButton"]

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QGridLayout(self)
            self.setLayout(layout)
            self.link_dict_edit = {}

        def isComplete(self):
            return True

        def initializePage(self, context: dict):
            # fetch the unlinked databases from the importer
            importer = context["importer"]
            link_dbs = set([exc["database"] for exc in importer.unlinked])
            layout = self.layout()

            for i, db in enumerate(link_dbs):
                if db == importer.db_name:
                    continue

                layout.addWidget(QtWidgets.QLabel(db), i, 0)

                drop_down = QtWidgets.QComboBox(self)
                drop_down.addItems(sorted(bd.databases))

                if db in bd.databases:
                    drop_down.setCurrentText(db)

                layout.addWidget(drop_down, i, 1)

                self.link_dict_edit[db] = drop_down

        def finalize(self, context: dict):
            importer = context["importer"]
            importer.apply_linking({k: v.currentText() for k, v in self.link_dict_edit.items()})

            context["linking_dict"] = {k: v.currentText() for k, v in self.link_dict_edit.items()}

        def nextPage(self):
            return ImportSetup.ConfirmPage

    class ConfirmPage(widgets.ABWizardPage):
        title = "Database Overview"
        subtitle = "Confirming and installing the database"
        buttonLayout = ["CustomButton1", "Stretch", "CancelButton", "CommitButton"]

        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QtWidgets.QGridLayout(self)
            self.setLayout(layout)

        def isComplete(self):
            return True

        def initializePage(self, context: dict):
            importer = context["importer"]
            layout = self.layout()
            row = 0
            for key, value in {
                "Database Name": importer.db_name,
                "Number of Activities": len(importer.data),
                "Number of Exchanges": sum(len(act.get("exchanges", [])) for act in importer.data),
                "Number of Unlinked Exchanges": len(list(importer.unlinked)),
            }.items():
                layout.addWidget(QtWidgets.QLabel(f"<b>{key}:</b>"), row, 0)
                layout.addWidget(QtWidgets.QLabel(str(value)), row, 1)
                row += 1

        def nextPage(self):
            return ImportSetup.InstallPage

    class InstallPage(widgets.ABThreadedWizardPage):
        title = "Importing Database"
        subtitle = "Importing database from .xlsx file"

        def __init__(self, parent=None):
            super().__init__(parent)
            self._import_database_name: str | None = None
            self.thread.finished.connect(self._reload_metadata_after_import)

        def _reload_metadata_after_import(self) -> None:
            if self._import_database_name and self._import_database_name in bd.databases:
                schedule_database_metadata_reload(self._import_database_name)

        class Thread(threading.ABThread):
            """Thread to handle the install process"""

            def run_safely(self, importer: ABExcelImporter, database_name: str, linking_dict: dict):
                """Download the ecoinvent release"""
                importer.write_database()

        def initializePage(self, context: dict):
            """Start the download thread"""
            self._import_database_name = context["database_name"]
            self.thread.start(
                context["importer"],
                self._import_database_name,
                context.get("linking_dict", {}),
            )

    pages = [ExtractPage, DatabaseName, DatabaseLink, ConfirmPage, InstallPage]


