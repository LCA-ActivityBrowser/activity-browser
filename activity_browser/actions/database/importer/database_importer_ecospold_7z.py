from logging import getLogger

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, threading, widgets, composites
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter

log = getLogger(__name__)


class DatabaseImporterEcospold7z(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = icons.qicons.import_db
    text = "Import database from ecospold .7z file"
    tool_tip = "Import database from ecospold .7z file"

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

        # show the setup dialog in wich the user can choose the name, and what biosphere database to use
        setup_dialog = ImportSetupDialog(application.main_window)
        if setup_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # initialize the import thread, setting needed attributes
        ei_thread = ImportEIThread(application)
        setattr(ei_thread, "path", path)
        setattr(ei_thread, "database_name", setup_dialog.database_name)
        setattr(ei_thread, "biosphere_name", setup_dialog.biosphere_name)

        # if we're importing biosphere as well, initialize that thread and run it first
        if setup_dialog.import_biosphere:
            # initialize the import thread, setting needed attributes
            bio_thread = ImportBiosphereThread(application)
            setattr(bio_thread, "path", path)
            setattr(bio_thread, "biosphere_name", setup_dialog.biosphere_name)

            # start the thread and run the ei importer after it has finished
            bio_thread.start()
            bio_thread.finished.connect(ei_thread.start)
        # if we're not also importing the biosphere, just start the ei import thread
        else:
            ei_thread.start()

        # setup a progress dialog
        progress_dialog = widgets.ABProgressDialog.get_connected_dialog("Importing database")

        # set the progress dialog to disappear when installation has finished, then show the dialog
        ei_thread.finished.connect(progress_dialog.deleteLater)
        progress_dialog.show()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name: str
    biosphere_name: str
    version: str
    model: str
    import_biosphere: bool

    def __init__(self, parent=None):
        super().__init__(parent)

        # create layouts
        self.setup_comp = composites.EcoinventSetupComposite()
        self.setup_comp.rejected.connect(self.reject)
        self.setup_comp.accepted.connect(self.accept)

        layout = QtWidgets.QVBoxLayout()
        #layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.setup_comp)
        self.setLayout(layout)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.setup_comp.get_database_name()
        self.biosphere_name = self.setup_comp.get_biosphere_name()
        self.import_biosphere = self.setup_comp.get_biosphere_choice() == "import"
        super().accept()


class ImportBiosphereThread(threading.ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_biosphere(self.biosphere_name)


class ImportEIThread(threading.ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_ecoinvent(self.database_name, self.biosphere_name)

