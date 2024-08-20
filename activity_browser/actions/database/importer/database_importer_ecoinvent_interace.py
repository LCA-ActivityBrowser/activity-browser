from logging import getLogger

import requests
import ecoinvent_interface as ei
from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance

from activity_browser import application
from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import layouts, widgets
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread
from activity_browser.ui.widgets import ABProgressDialog
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter

log = getLogger(__name__)


class DatabaseImporterEcoinventInterface(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = qicons.import_db
    text = "Import database from ecoinvent"
    tool_tip = "Import database from ecoinvent"

    @staticmethod
    @exception_dialogs
    def run():
        # show the setup dialog in wich the user can choose the name, and what biosphere database to use
        setup_dialog = ImportSetupDialog()
        if setup_dialog.exec_() == QtWidgets.QDialog.Rejected:
            return

        # initialize the import thread, setting needed attributes
        ei_thread = ImportEIThread(application)
        setattr(ei_thread, "database_name", setup_dialog.database_name)
        setattr(ei_thread, "biosphere_name", setup_dialog.biosphere_name)
        setattr(ei_thread, "import_biosphere", setup_dialog.import_biosphere)
        setattr(ei_thread, "version", setup_dialog.version)
        setattr(ei_thread, "model", setup_dialog.model)

        # setup a progress dialog
        progress_dialog = ABProgressDialog.get_connected_dialog("Importing database")

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

    def __init__(self, parent=None):
        super().__init__(parent)

        # create layouts
        self.login_layout = EcoinventLoginLayout()
        self.login_layout.rejected.connect(self.reject)
        self.login_layout.accepted.connect(self.to_setup_layout)

        self.setLayout(self.login_layout)

    def to_setup_layout(self):
        setup_layout = EcoinventSetupLayout(self.login_layout.release)
        QtWidgets.QWidget().setLayout(self.layout())

        setup_layout.rejected.connect(self.reject)
        setup_layout.accepted.connect(self.accept)

        self.setLayout(setup_layout)

    def accept(self):
        """Correctly set the dialog's attributes for further use in the action"""
        layout: EcoinventSetupLayout = self.layout()
        self.database_name = layout.get_database_name()
        self.biosphere_name = layout.get_biosphere_name()
        self.import_biosphere = layout.get_biosphere_choice() == "import"
        self.version = layout.get_version()
        self.model = layout.get_model()
        super().accept()


class EcoinventLoginLayout(layouts.LoginLayout):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self):
        self.settings = ei.Settings()
        self.release: ei.EcoinventRelease = None

        super().__init__(
            label="Provide your ecoinvent credentials",
            username_placeholder="ecoinvent username",
            password_placeholder="ecoinvent password",
            username_preset=self.settings.username,
            password_preset=self.settings.password,
        )

        self.buttons = layouts.HorizontalButtonsLayout("Cancel", "~Login")
        self.buttons["Login"].setEnabled(self.validate())
        self.valid.connect(self.buttons["Login"].setEnabled)

        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Login"].clicked.connect(self.credential_check)

        self.addLayout(self.buttons)

    def credential_check(self):
        # set waitcursor because we're making http requests which take long
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # set the provided settings and check if we can get a version list (i.e. logon was succesful)
        try:
            self.settings = ei.Settings(
                username=self.username.text(),
                password=self.password.text()
            )
            self.release = ei.EcoinventRelease(self.settings)
            self.release.list_versions()

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


class EcoinventSetupLayout(layouts.DatabaseNameLayout):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self, release: ei.EcoinventRelease):
        super().__init__(
            label="Set ecoinvent database name"
        )
        self.release = release

        # set up the version & model comboboxes
        self.versions = QtWidgets.QComboBox()
        self.models = QtWidgets.QComboBox()
        self.versions.currentTextChanged.connect(self.collect_models)
        self.versions.addItems(self.release.list_versions())

        # setup the biosphere choice section
        self.biosphere_choice = layouts.RadioButtonCollapseLayout()
        self.biosphere_choice.add_option(
            name="existing",
            label="Link to an existing biosphere",
            view=widgets.ABComboBox.get_database_combobox()
        )
        self.biosphere_choice.button("existing").clicked.connect(self.validate)
        self.biosphere_choice.add_option(
            name="import",
            label="Import included biosphere",
            view=layouts.DatabaseNameLayout(label=None, database_placeholder="Set biosphere name")
        )
        self.biosphere_choice.button("import").clicked.connect(self.validate)
        self.biosphere_choice.view("import").database_name.textChanged.connect(self.validate)

        self.buttons = layouts.HorizontalButtonsLayout("Cancel", "*~Download")
        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Download"].clicked.connect(self.accepted.emit)

        self.addWidget(QtWidgets.QLabel("Choose ecoinvent version"))
        self.addWidget(self.versions)
        self.addWidget(self.models)
        self.addLayout(self.biosphere_choice)
        self.addLayout(self.buttons)

        self.database_name.textChanged.connect(self.validate)

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

    def validate(self):
        valid = (
            bool(self.get_database_name())
            and (
                self.get_biosphere_choice() == "existing"
                or (
                    self.get_biosphere_choice() == "import"
                    and self.get_biosphere_name()
                )
            )
        )
        self.buttons["Download"].setEnabled(valid)


class ImportEIThread(ABThread):
    database_name: str
    biosphere_name: str
    version: str
    model: str
    import_biosphere: bool

    def run_safely(self):
        release = ABEcoinventRelease(ei.Settings())
        path = release.get_release(
            version=self.version,
            system_model=self.model,
            release_type=ei.ReleaseType.ecospold,
            extract=False,
            fix_version=False
        )
        importer = Ecoinvent7zImporter(str(path) + ".7z")
        if self.import_biosphere:
            importer.install_biosphere(self.biosphere_name)
        importer.install_ecoinvent(self.database_name, self.biosphere_name)


if __name__ == '__main__':
    dialog = ImportSetupDialog()
    dialog.show()

    application.exec_()

