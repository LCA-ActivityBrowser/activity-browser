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

        self.setWindowTitle("Project Setup")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.setWindowFlags(QtCore.Qt.Sheet)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        self.setPage(self.choose_setup, ChooseSetupPage(self))
        self.setPage(self.ecoinvent_login, EcoInventLoginPage(self))
        self.setPage(self.ecoinvent_version, EcoInventVersionPage(self))
        self.setPage(self.install_page, InstallPage(self))

        self.setStartId(self.choose_setup)

        self.type = None  # set on the first page


class ChooseSetupPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Setup type")
        self.setSubTitle("Choose how you want to set up you project")

        radio_1 = QtWidgets.QRadioButton("Biosphere3")
        radio_2 = QtWidgets.QRadioButton("ecoinvent and Biosphere3")
        radio_1.setChecked(True)

        self.buttons = QtWidgets.QButtonGroup()
        self.buttons.addButton(radio_1, ProjectSetupWizard.install_page)
        self.buttons.addButton(radio_2, ProjectSetupWizard.ecoinvent_login)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(radio_1)
        layout.addWidget(radio_2)

        self.setLayout(layout)

    def nextId(self):
        choice = "ecoinvent" if self.buttons.checkedId() == ProjectSetupWizard.ecoinvent_login else "default"
        self.wizard().type = choice
        return self.buttons.checkedId()


class EcoInventLoginPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Login")
        self.setSubTitle("Login with your ecoinvent credentials to authorize the download")

        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText('ecoinvent username')
        self.registerField("username*", self.username)

        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText('ecoinvent password'),
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.registerField("password*", self.password)

        self.message = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.message)

        self.setLayout(layout)

    def initializePage(self):
        settings = ei.Settings()
        self.username.setText(settings.username)
        self.password.setText(settings.password)

    def validatePage(self):
        try:
            settings = ei.Settings(username=self.username.text(), password=self.password.text())
            release = ei.EcoinventRelease(settings)
            release.list_versions()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.message.setText("Invalid username and/or password, please try again.")
                return False
            else:
                self.message.setText("Unknown connection error, try again later.")
                raise e

        self.setField("release", release)
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

        self.versions = QtWidgets.QComboBox(self)
        self.models = QtWidgets.QComboBox(self)

        self.registerField("version", self.versions, "currentText", "currentTextChanged")
        self.registerField("model", self.models, "currentText", "currentTextChanged")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.versions)
        layout.addWidget(self.models)

        self.setLayout(layout)

    def initializePage(self):
        settings = ei.Settings(username=self.field("username"), password=self.field("password"))
        release = ei.EcoinventRelease(settings)

        def collect_models_slot(version: str):
            self.models.clear()
            self.models.addItems(release.list_system_models(version))

        self.versions.currentTextChanged.connect(collect_models_slot)
        self.versions.addItems(release.list_versions())


class InstallPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.thread= None

        self.setTitle("Setting up")
        self.setSubTitle("Setting up your project")

        self.progress = QtWidgets.QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)

        self.info = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.progress)
        layout.addWidget(self.info)

        self.setLayout(layout)

    def initializePage(self):
        self.wizard().setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.wizard().show()

        self.wizard().button(QtWidgets.QWizard.BackButton).hide()

        if self.wizard().type == "ecoinvent":
            self.thread = EcoinventInstallThread(self.field("version"), self.field("model"), self)
        else:
            self.thread = DefaultInstallThread(self)

        self.thread.status.connect(self.status_update)
        self.thread.finished.connect(self.completeChanged.emit)
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
    def __init__(self, version, model, parent=None):
        super().__init__(parent)
        self.version = version
        self.model = model

    def run_safely(self):
        ab_import_ecoinvent_release(
            self.version,
            self.model,
            lambda x, y: None
        )


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
