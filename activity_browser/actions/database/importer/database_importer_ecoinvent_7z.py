from logging import getLogger

from PySide2 import QtWidgets, QtCore

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.mod.tqdm import qt_tqdm
from activity_browser.mod.pyprind import qt_pyprind
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter

log = getLogger(__name__)


class DatabaseImporterEcoinvent7z(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from ecoinvent .7z file"
    tool_tip = "Import database from ecoinvent .7z file"

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
        setup_dialog = ImportSetupDialog()
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
        progress_dialog = QtWidgets.QProgressDialog(application.main_window)
        progress_dialog.setWindowTitle("Import database")
        progress_dialog.setLabelText("Initializing")
        progress_dialog.setAutoReset(False)
        progress_dialog.setCancelButton(None)

        # connect to tqdm progress bars
        qt_tqdm.updated.connect(lambda text, _: progress_dialog.setLabelText(text))
        qt_tqdm.updated.connect(lambda _, progress: progress_dialog.setValue(int(progress)))

        # connect to pyprind progress bars
        qt_pyprind.updated.connect(lambda text, _: progress_dialog.setLabelText(text))
        qt_pyprind.updated.connect(lambda _, progress: progress_dialog.setValue(int(progress)))

        # set the progress dialog to disappear when installation has finished, then show the dialog
        ei_thread.finished.connect(progress_dialog.deleteLater)
        progress_dialog.show()


class ImportSetupDialog(QtWidgets.QDialog):
    database_name = None
    biosphere_name = None
    import_biosphere = False
    
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create db name textbox
        self.db_name_textbox = QtWidgets.QLineEdit()
        self.db_name_textbox.setPlaceholderText("Database name")
        self.db_name_textbox.textChanged.connect(self.db_name_check)

        # Create warning text for when the user enters a database that already exists
        self.db_name_warning = QtWidgets.QLabel()
        self.db_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.db_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing database will be overwritten</p>")
        self.db_name_warning.setHidden(True)

        # Create biosphere choice buttons
        self.existing_bio_radio = QtWidgets.QRadioButton("Link to an existing biosphere")
        self.import_bio_radio = QtWidgets.QRadioButton("Import bundled biosphere")

        self.existing_bio_radio.clicked.connect(self.select_existing_bio)
        self.import_bio_radio.clicked.connect(self.select_import_bio)

        # Add radio buttons to a button group
        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(self.existing_bio_radio, id=1)
        self.button_group.addButton(self.import_bio_radio, id=2)

        # Drop-down for an existing biosphere
        self.bio_name_dropdown = QtWidgets.QComboBox(self)
        self.bio_name_dropdown.addItems(bd.databases)
        self.bio_name_dropdown.setHidden(True)

        # Text-box for bundled biosphere
        self.bio_name_textbox = QtWidgets.QLineEdit()
        self.bio_name_textbox.setPlaceholderText("New biosphere name")
        self.bio_name_textbox.setHidden(True)
        self.bio_name_textbox.textChanged.connect(self.bio_name_check)

        # Create warning text for when the user enters a biosphere database that already exists
        self.bio_name_warning = QtWidgets.QLabel()
        self.bio_name_warning.setTextFormat(QtCore.Qt.RichText)
        self.bio_name_warning.setText(
            "<p style='color: red; font-size: small;'>Existing biosphere will be overwritten</p>")
        self.bio_name_warning.setHidden(True)

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
        layout.addWidget(self.existing_bio_radio)
        layout.addWidget(self.bio_name_dropdown)
        layout.addWidget(self.import_bio_radio)
        layout.addWidget(self.bio_name_textbox)
        layout.addWidget(self.bio_name_warning)
        layout.addLayout(button_layout)

        # Set the dialog layout
        self.setLayout(layout)

    def select_existing_bio(self):
        """Slot for when the existing bio radio button is clicked, hide the correct widgets and validate"""
        self.bio_name_textbox.setHidden(True)
        self.bio_name_dropdown.setHidden(False)
        self.validate()

    def select_import_bio(self):
        """Slot for when the import bio radio button is clicked, hide the correct widgets and validate"""
        self.bio_name_dropdown.setHidden(True)
        self.bio_name_textbox.setHidden(False)
        self.validate()

    def db_name_check(self):
        """Slot for when the db_name_textbox is changed, hide/show the warning and validate"""
        if self.db_name_textbox.text() in bd.databases:
            self.db_name_warning.setHidden(False)
        else:
            self.db_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def bio_name_check(self):
        """Slot for when the bio_name_textbox is changed, hide/show the warning and validate"""
        if self.bio_name_textbox.text() in bd.databases:
            self.bio_name_warning.setHidden(False)
        else:
            self.bio_name_warning.setHidden(True)
        self.window().adjustSize()
        self.validate()

    def validate(self):
        """Validate the user input and enable the OK button if all is clear"""
        valid = (
            bool(self.db_name_textbox.text()) and (
                self.existing_bio_radio.isChecked() or (
                    self.import_bio_radio.isChecked() and
                    bool(self.bio_name_textbox.text())
                )
            )
        )
        self.ok_button.setEnabled(valid)
    
    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.db_name_textbox.text()
        if self.import_bio_radio.isChecked():
            self.import_biosphere = True
            self.biosphere_name = self.bio_name_textbox.text()
        else:
            self.biosphere_name = self.bio_name_dropdown.currentText()
        super().accept()


class ImportBiosphereThread(ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_biosphere(self.biosphere_name)


class ImportEIThread(ABThread):
    def run_safely(self):
        importer = Ecoinvent7zImporter(self.path)
        importer.install_ecoinvent(self.database_name, self.biosphere_name)

