from logging import getLogger

import requests
import ecoinvent_interface as ei
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.ui import layouts, widgets, icons, threading
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter

from .database_importer_ecospold_7z import EcoinventSetupLayout

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
        self.login_layout = EcoinventInterfaceLoginLayout()
        self.login_layout.rejected.connect(self.reject)
        self.login_layout.accepted.connect(self.to_setup_layout)

        # create setup layout
        self.setup_layout = EcoinventInterfaceSetupLayout()
        self.setup_layout.rejected.connect(self.reject)
        self.setup_layout.accepted.connect(self.accept)

        # create final layout
        self.stack = widgets.ABStackedLayout(self)
        self.stack.addLayout(self.login_layout)
        self.stack.addLayout(self.setup_layout)

        self.setLayout(self.stack)

    def to_setup_layout(self):
        """
        Switch to the setup layout by deleting the login layout and setting a new layout.
        """
        self.setup_layout.load(self.ei_release)
        self.stack.setCurrentIndex(1)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        self.database_name = self.setup_layout.get_database_name()
        self.biosphere_name = self.setup_layout.get_biosphere_name()
        self.import_biosphere = self.setup_layout.get_biosphere_choice() == "import"
        self.version = self.setup_layout.get_version()
        self.model = self.setup_layout.get_model()
        super().accept()


class EcoinventInterfaceLoginLayout(layouts.LoginLayout):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self):
        self.settings = ei.Settings()

        # initialize with a special focus on ecoinvent credentials
        super().__init__(
            label="Provide your ecoinvent credentials",
            username_placeholder="ecoinvent username",
            password_placeholder="ecoinvent password",
            username_preset=self.settings.username,
            password_preset=self.settings.password,
        )

        # set up the buttons and connect
        self.buttons = layouts.HorizontalButtonsLayout("Cancel", "~Login")
        self.buttons["Login"].setEnabled(self.validate())
        self.valid.connect(self.buttons["Login"].setEnabled)

        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Login"].clicked.connect(self.credential_check)

        # add buttons to self
        self.addLayout(self.buttons)

    def credential_check(self):
        """
        Check whether the supplied credentials are valid by instantiating an EcoinventInterface.Release
        and seeing if we can request a list of available versions from it.
        """
        # set waitcursor because we're making http requests which take long
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # set the provided settings and check if we can get a version list (i.e. logon was succesful)
        try:
            self.settings = ei.Settings(
                username=self.username.text(),
                password=self.password.text()
            )
            dialog = application.main_window.findChild(ImportSetupDialog)
            dialog.ei_release = ABEcoinventRelease(self.settings)
            dialog.ei_release.list_versions()

        # logon was unsuccesful
        except requests.exceptions.HTTPError as e:
            QtWidgets.QApplication.restoreOverrideCursor()

            # in case of 401: Unauthorized, we prompt for a retry of logon
            if e.response.status_code == 401:
                self.warning.setText("Invalid username and/or password, please try again.")
                self.warning.setVisible(True)
                return False
            # else, other HTTPError, try again later maybe? Raise exception for logging
            else:
                self.warning.setText("Unknown connection error, try again later.")
                self.warning.setVisible(True)
                raise e

        # in case of success, set the settings for permanent use
        ei.permanent_setting("username", self.username.text())
        ei.permanent_setting("password", self.password.text())

        # emit accepted signal
        self.accepted.emit()
        QtWidgets.QApplication.restoreOverrideCursor()


class EcoinventInterfaceSetupLayout(EcoinventSetupLayout):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    release: ABEcoinventRelease

    def __init__(self):
        super().__init__()

        # set up the version & model comboboxes
        self.versions = QtWidgets.QComboBox()
        self.models = QtWidgets.QComboBox()

        # insert underneath the name choice
        self.insertWidget(3, QtWidgets.QLabel("Choose ecoinvent version"))
        self.insertWidget(4, self.versions)
        self.insertWidget(5, self.models)

    def load(self, release: ABEcoinventRelease):
        self.release = release
        self.versions.currentTextChanged.connect(self.collect_models)
        self.versions.addItems(self.release.list_versions())

    def get_version(self) -> str:
        return self.versions.currentText()

    def get_model(self) -> str:
        return self.models.currentText()

    def collect_models(self, version: str):
        """Slot for when the version selection changes"""
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.models.clear()
        self.models.addItems(self.release.list_system_models(version))
        QtWidgets.QApplication.restoreOverrideCursor()


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
