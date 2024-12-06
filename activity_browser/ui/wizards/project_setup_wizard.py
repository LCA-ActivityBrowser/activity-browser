import ecoinvent_interface as ei
import requests
from PySide2 import QtWidgets, QtCore

from activity_browser.ui.threading import ABThread
from activity_browser.mod.bw2io import ab_bw2setup
from activity_browser.mod.bw2io.ecoinvent import ab_import_ecoinvent_release
from activity_browser.utils import sort_semantic_versions
from activity_browser.info import __ei_versions__


class ProjectSetupWizard(QtWidgets.QWizard):
    choose_setup = 1
    ecoinvent_login = 2
    ecoinvent_version = 3
    biosphere_version = 4
    install_page = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        # setting wizard options
        self.setWizardStyle(self.ModernStyle)
        self.setOption(self.NoCancelButtonOnLastPage)
        self.setOption(self.NoBackButtonOnLastPage)
        self.setOption(self.NoCancelButton, False)

        # setting window options
        self.setWindowTitle("Project Setup")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Sheet)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)

        # initializing and setting all pages
        self.setPage(self.choose_setup, ChooseSetupPage(self))
        self.setPage(self.ecoinvent_login, EcoInventLoginPage(self))
        self.setPage(self.ecoinvent_version, EcoInventVersionPage(self))
        self.setPage(self.biosphere_version, DefaultVersionPage(self))
        self.setPage(self.install_page, InstallPage(self))

        self.type = None  # set on the first page


class ChooseSetupPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Setup type")
        self.setSubTitle("Choose how you want to set up you project")

        # radio buttons for the setup mode
        radio_1 = QtWidgets.QRadioButton("Biosphere3")
        radio_2 = QtWidgets.QRadioButton("ecoinvent and Biosphere3")
        radio_1.setChecked(True)

        # join the buttons in a buttongroup, id of the button is the id of the next page for that choice
        self.buttons = QtWidgets.QButtonGroup()
        self.buttons.addButton(radio_1, ProjectSetupWizard.biosphere_version)
        self.buttons.addButton(radio_2, ProjectSetupWizard.ecoinvent_login)

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(radio_1)
        layout.addWidget(radio_2)

        self.setLayout(layout)

    def nextId(self):
        # next page is based on decision
        choice = "ecoinvent" if self.buttons.checkedId() == ProjectSetupWizard.ecoinvent_login else "default"

        # set the choice on the wizard, can't get setField() to work
        self.wizard().type = choice

        # id of the button is the id of the next page
        return self.buttons.checkedId()


class DefaultVersionPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Choose version")
        self.setSubTitle("Choose biosphere version")

        # set combobox for version selection
        self.versions = QtWidgets.QComboBox(self)
        self.versions.addItems(sort_semantic_versions(__ei_versions__))

        # register fields for said comboboxes
        self.registerField("bio-version", self.versions, "currentText", "currentTextChanged")

        # set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.versions)

        self.setLayout(layout)



class EcoInventLoginPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Login")
        self.setSubTitle("Login with your ecoinvent credentials to authorize the download")

        # create username field
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText('ecoinvent username')
        self.registerField("username*", self.username)

        # create password field and set hidden
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText('ecoinvent password'),
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.registerField("password*", self.password)

        # empty message for now, will be used in case of wrong password or other error
        self.message = QtWidgets.QLabel()

        # set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.message)

        self.setLayout(layout)

    def initializePage(self):
        # on initialization set stored username & password
        settings = ei.Settings()
        self.username.setText(settings.username)
        self.password.setText(settings.password)

    def validatePage(self):
        # set waitcursor because we're making http requests which take long
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # set the provided settings and check if we can get a version list (i.e. logon was succesful)
        try:
            settings = ei.Settings(username=self.username.text(), password=self.password.text())
            release = ei.EcoinventRelease(settings)
            release.list_versions()

        except requests.exceptions.HTTPError as e:
            QtWidgets.QApplication.restoreOverrideCursor()

            # in case of 401: Unauthorized, we prompt for a retry of logon
            if e.response.status_code == 401:
                self.message.setText("Invalid username and/or password, please try again.")
                return False
            # else, other HTTPError, try again later maybe? Raise exception for logging
            else:
                self.message.setText("Unknown connection error, try again later.")
                raise e

        except requests.exceptions.ConnectionError:
            QtWidgets.QApplication.restoreOverrideCursor()
            self.message.setText("Cannot connect to the internet, please try again later.")
            return False

        except Exception as e:
            # restore cursor on all exceptions
            QtWidgets.QApplication.restoreOverrideCursor()
            raise e

        # in case of success, set the settings for permanent use
        ei.permanent_setting("username", self.username.text())
        ei.permanent_setting("password", self.password.text())
        return True

    def nextId(self):
        return ProjectSetupWizard.ecoinvent_version


class EcoInventVersionPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Choose version")
        self.setSubTitle("Choose ecoinvent version and system model")

        # set comboboxes for version and model selections
        self.versions = QtWidgets.QComboBox(self)
        self.models = QtWidgets.QComboBox(self)

        # register fields for said comboboxes
        self.registerField("version", self.versions, "currentText", "currentTextChanged")
        self.registerField("model", self.models, "currentText", "currentTextChanged")

        # set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.versions)
        layout.addWidget(self.models)

        self.setLayout(layout)

    def initializePage(self):
        # at this point settings are always saved, get a release with them
        settings = ei.Settings()
        release = ei.EcoinventRelease(settings)

        def collect_models_slot(version: str):
            """Slot for when the version selection changes"""
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.models.clear()
            self.models.addItems(release.list_system_models(version))
            QtWidgets.QApplication.restoreOverrideCursor()

        # populate versions list with available versions, and update models if the version selection changes
        self.versions.currentTextChanged.connect(collect_models_slot)
        self.versions.addItems(release.list_versions())

        # restore override cursor from last page
        QtWidgets.QApplication.restoreOverrideCursor()

    def nextId(self):
        return self.wizard().install_page


class InstallPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.install_thread = None  # will be ei or default install thread

        self.setTitle("Setting up")
        self.setSubTitle("Setting up your project")

        # setup progressbar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)

        # setup infobar
        self.info = QtWidgets.QLabel()

        # set layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.progress)
        layout.addWidget(self.info)

        self.setLayout(layout)

    def initializePage(self):
        self.wizard().button(QtWidgets.QWizard.BackButton).hide()

        if self.wizard().type == "ecoinvent":
            self.install_thread = EcoinventInstallThread(self)
        else:
            self.install_thread = DefaultInstallThread(self)

        self.install_thread.status.connect(self.status_update)
        self.install_thread.finished.connect(self.completeChanged.emit)
        self.install_thread.finished.connect(lambda: self.status_update(100, "Done"))
        self.install_thread.start()

    def isComplete(self):
        return self.install_thread.isFinished()

    def status_update(self, progress: int | None, message: str):
        if isinstance(progress, int):
            self.progress.setRange(0, 100)
            self.progress.setValue(progress)
        if not progress:
            self.progress.setRange(0, 0)
        self.info.setText(message)


class DefaultInstallThread(ABThread):

    def run_safely(self):
        ab_bw2setup(self.parent().field("bio-version"))


class EcoinventInstallThread(ABThread):

    def run_safely(self):
        ab_import_ecoinvent_release(self.parent().field("version"), self.parent().field("model"))

