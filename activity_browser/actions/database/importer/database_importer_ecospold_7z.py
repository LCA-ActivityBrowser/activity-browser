from logging import getLogger

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, threading, widgets, layouts
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
        self.login_layout = EcoinventSetupLayout()
        self.login_layout.rejected.connect(self.reject)
        self.login_layout.accepted.connect(self.accept)

        self.setLayout(self.login_layout)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.login_layout.get_database_name()
        self.biosphere_name = self.login_layout.get_biosphere_name()
        self.import_biosphere = self.login_layout.get_biosphere_choice() == "import"
        super().accept()


class EcoinventSetupLayout(layouts.DatabaseNameLayout):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self):
        # initialize superclass with an ecoinvent focus
        super().__init__(
            label="Set ecoinvent database name"
        )
        # validate when the database name is changed by the user
        self.database_name.textChanged.connect(self.validate)

        # setup the biosphere choice section
        self.biosphere_choice = layouts.RadioButtonCollapseLayout()

        # add option to connect to an existing biosphere database
        self.biosphere_choice.add_option(
            name="existing",
            label="Link to an existing biosphere",
            view=widgets.ABComboBox.get_database_combobox()
        )
        self.biosphere_choice.button("existing").clicked.connect(self.validate)

        # add option to install the supplied biosphere database
        self.biosphere_choice.add_option(
            name="import",
            label="Import included biosphere",
            view=layouts.DatabaseNameLayout(label=None, database_placeholder="Set biosphere name")
        )
        self.biosphere_choice.button("import").clicked.connect(self.validate)
        self.biosphere_choice.view("import").database_name.textChanged.connect(self.validate)

        # set up the buttons at the bottom of the layout and connect the signals
        self.buttons = layouts.HorizontalButtonsLayout("Cancel", "*~Import")
        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Import"].clicked.connect(self.accepted.emit)

        # finalize the layout
        self.addLayout(self.biosphere_choice)
        self.addLayout(self.buttons)

        self.validate()

    def get_database_name(self) -> str:
        return self.database_name.text()

    def get_biosphere_choice(self) -> None | str:
        return self.biosphere_choice.current_option()

    def get_biosphere_name(self) -> None | str:
        choice = self.get_biosphere_choice()
        if choice == "existing":
            return self.biosphere_choice.view(choice).currentText()
        if choice == "import":
            return self.biosphere_choice.view(choice).database_name.text()
        else:
            return None

    def validate(self):
        valid = (
            bool(self.get_database_name())
            and (
                self.get_biosphere_choice() == "existing"
                or (
                    self.get_biosphere_choice() == "import"
                    and bool(self.get_biosphere_name())
                )
            )
        )
        self.buttons["Import"].setEnabled(valid)


class ImportBiosphereThread(threading.ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_biosphere(self.biosphere_name)


class ImportEIThread(threading.ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_ecoinvent(self.database_name, self.biosphere_name)

