import os
import ecoinvent_interface as ei
import requests
from PySide2 import QtWidgets, QtCore

from activity_browser.ui.threading import ABThread
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2io import ab_bw2setup
from activity_browser.mod.bw2io.ecoinvent import ab_import_ecoinvent_release


class ProjectSetupWizard(QtWidgets.QWizard):
    choose_setup = 1
    ecoinvent_login = 2
    ecoinvent_version = 3
    install_page = 4

    def __init__(self, parent=None):
        super().__init__(parent)

        # setting wizard options
        self.setWizardStyle(self.ModernStyle)
        self.setOption(self.NoCancelButtonOnLastPage)
        self.setOption(self.NoBackButtonOnLastPage)

        # setting window options
        self.setWindowTitle("Project Setup")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Sheet)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        # initializing and setting all pages
        self.setPage(self.choose_setup, ChooseSetupPage(self))
        self.setPage(self.ecoinvent_login, EcoInventLoginPage(self))
        self.setPage(self.ecoinvent_version, EcoInventVersionPage(self))
        self.setPage(self.install_page, InstallPage(self))

        # self.setStartId(self.choose_setup)

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
        self.buttons.addButton(radio_1, ProjectSetupWizard.install_page)
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

        # logon was unsuccesful
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


class InstallPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.thread = None  # will be ei or default install thread

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
        self.wizard().setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.wizard().show()

        self.wizard().button(QtWidgets.QWizard.BackButton).hide()

        if self.wizard().type == "ecoinvent":
            self.thread = EcoinventInstallThread(self)
        else:
            self.thread = DefaultInstallThread(self)

        self.thread.status.connect(self.status_update)
        self.thread.finished.connect(self.completeChanged.emit)
        self.thread.finished.connect(lambda: self.status_update(100, "Done"))
        self.thread.start()

    def isComplete(self):
        return self.thread.isFinished()

    def status_update(self, progress: int | None, message: str):
        if isinstance(progress, int):
            self.progress.setRange(0, 100)
            self.progress.setValue(progress)
        if not progress:
            self.progress.setRange(0, 0)
        self.info.setText(message)


class DefaultInstallThread(ABThread):

    def run_safely(self):
        ab_bw2setup()


class EcoinventInstallThread(ABThread):

    def run_safely(self):
        ab_import_ecoinvent_release(self.parent().field("version"), self.parent().field("model"))


if __name__ == "__main__":
    import sys, logging
    from activity_browser import application
    from activity_browser.layouts.main import MainWindow

    try:
        bd.projects.delete_project("testing_ei", True)
    except:
        pass

    logging.root.setLevel("INFO")

    bd.projects.set_current("testing_ei")

    application.main_window = MainWindow(application)

    wizard = ProjectSetupWizard(application.main_window)

    application.show()
    wizard.show()

    sys.exit(application.exec_())
