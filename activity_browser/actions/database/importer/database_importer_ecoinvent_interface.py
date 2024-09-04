from logging import getLogger

import ecoinvent_interface as ei
from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.ui import widgets, icons, threading, composites
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter


log = getLogger(__name__)


class DatabaseImporterEcoinventInterface(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = icons.qicons.import_db
    text = "Import database from ecoinvent"
    tool_tip = "Import database from ecoinvent"

    @staticmethod
    @exception_dialogs
    def run():
        # show the setup dialog in which the user can first login and then choose the name of the database
        # and whether to import the accompanied biosphere, or connect to an existing biosphere
        setup_dialog = ImportSetupDialog(application.main_window)
        if setup_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # initialize the import thread, setting needed attributes
        ei_thread = ImportEIThread(application)
        setattr(ei_thread, "database_name", setup_dialog.database_name)
        setattr(ei_thread, "biosphere_name", setup_dialog.biosphere_name)
        setattr(ei_thread, "import_biosphere", setup_dialog.import_biosphere)
        setattr(ei_thread, "version", setup_dialog.version)
        setattr(ei_thread, "model", setup_dialog.model)
        setattr(ei_thread, "release", setup_dialog.ei_release)

        # setup a progress dialog
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing database")

        # set the progress dialog to disappear when installation has finished, then show the dialog
        ei_thread.finished.connect(progress_dialog.deleteLater)
        progress_dialog.show()
        ei_thread.start()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name: str
    biosphere_name: str
    version: str
    model: str
    import_biosphere: bool
    ei_release: ABEcoinventRelease

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import from ecoinvent")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        # create login layout
        self.login_comp = composites.EcoinventInterfaceLoginComposite(self)
        self.login_comp.rejected.connect(self.reject)
        self.login_comp.accepted.connect(self.to_setup_layout)

        # create setup layout
        self.setup_comp = composites.EcoinventInterfaceSetupComposite()
        self.setup_comp.rejected.connect(self.reject)
        self.setup_comp.accepted.connect(self.accept)

        # create final layout
        self.stack = widgets.ABStackedLayout(self)
        self.stack.addWidget(self.login_comp)
        self.stack.addWidget(self.setup_comp)

        self.setLayout(self.stack)

    def to_setup_layout(self):
        """
        Switch to the setup layout by deleting the login layout and setting a new layout.
        """
        self.setup_comp.load(self.ei_release)
        self.stack.setCurrentIndex(1)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.setup_comp.get_database_name()
        self.biosphere_name = self.setup_comp.get_biosphere_name()
        self.import_biosphere = self.setup_comp.get_biosphere_choice() == "import"
        self.version = self.setup_comp.get_version()
        self.model = self.setup_comp.get_model()
        super().accept()


class ImportEIThread(threading.ABThread):
    database_name: str
    biosphere_name: str
    version: str
    model: str
    import_biosphere: bool
    release: ABEcoinventRelease

    def run_safely(self):
        path = self.release.get_release(
            version=self.version,
            system_model=self.model,
            release_type=ei.ReleaseType.ecospold,
            extract=False,
            fix_version=False
        )

        # format the path
        path = str(path)
        if not path.endswith(".7z"):
            path = path + ".7z"

        # start the import
        importer = Ecoinvent7zImporter(path)
        if self.import_biosphere:
            importer.install_biosphere(self.biosphere_name)
        importer.install_ecoinvent(self.database_name, self.biosphere_name)
