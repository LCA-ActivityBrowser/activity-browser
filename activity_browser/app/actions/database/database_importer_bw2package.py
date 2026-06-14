import os

from qtpy import QtWidgets

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.app.actions.database.database_relink import DatabaseLinkingDialog
from activity_browser.ui import icons, widgets
from activity_browser.bwutils.importers import ABPackage
from activity_browser.bwutils.metadata.loader import schedule_database_metadata_reload
from activity_browser.ui.core import threading




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
            parent=app.main_window,
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
        import_dialog = ImportSetup(parent=app.main_window, title="Import Database", context=context)
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
            if ABPackage.missing_dependencies(self.context()["path"]):
                return ImportSetup.DatabaseLink
            return ImportSetup.InstallPage

    class DatabaseLink(widgets.ABWizardPage):
        title = "Link Databases"
        subtitle = "Match package databases to databases in this project"

        def isComplete(self):
            return bool(self.context().get("relink_ready"))

        def initializePage(self, context: dict):
            context["relink_ready"] = False
            missing = ABPackage.missing_dependencies(context["path"])
            if not missing:
                context["relink"] = {}
                context["relink_ready"] = True
                return

            options = [(db, sorted(bd.databases)) for db in sorted(missing)]
            dialog = DatabaseLinkingDialog.relink_bw2package(
                options, parent=self.wizard()
            )
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                self.wizard().reject()
                return

            relink = {db: dialog.links[db] for db in missing}
            if any(db not in bd.databases for db in relink.values()):
                QtWidgets.QMessageBox.warning(
                    self.wizard(),
                    "Database linking required",
                    "Each missing database must be linked to a database in this project.",
                )
                self.wizard().reject()
                return

            context["relink"] = relink
            context["relink_ready"] = True
            self.completeChanged.emit()

        def nextPage(self):
            return ImportSetup.InstallPage

    class InstallPage(widgets.ABThreadedWizardPage):
        """Wizard page to install the selected bw2package"""
        title = "Importing Database"
        subtitle = "Importing database from .bw2package file"

        def __init__(self, parent=None):
            super().__init__(parent)
            self._import_database_name: str | None = None
            self.thread.finished.connect(self._reload_metadata_after_import)

        def _reload_metadata_after_import(self) -> None:
            if self._import_database_name and self._import_database_name in bd.databases:
                schedule_database_metadata_reload(self._import_database_name)

        class Thread(threading.ABThread):
            """Thread to handle the install process"""
            def run_safely(self, path: str, db_name: str, relink: dict | None = None):
                ABPackage.import_file(path, rename=db_name, relink=relink or {})

        def initializePage(self, context: dict):
            """Start the download thread"""
            self._import_database_name = context["database_name"]
            self.thread.start(
                context["path"],
                self._import_database_name,
                context.get("relink", {}),
            )

    pages = [DatabaseName, DatabaseLink, InstallPage]

