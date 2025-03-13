from logging import getLogger
from copy import deepcopy

import requests

import ecoinvent_interface as ei
import bw2data as bd

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, SignalInstance, Qt

from activity_browser import application, signals
from activity_browser.ui import widgets, icons, threading, composites
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter
from activity_browser.bwutils.io.ecoinvent_lcia_importer import EcoinventLCIAImporter


log = getLogger(__name__)


class DatabaseImportFromEcoinvent(ABAction):
    """ABAction to open the DatabaseImportWizard"""

    icon = icons.qicons.import_db
    text = "Import database from ecoinvent"
    tool_tip = "Import database from ecoinvent"

    @staticmethod
    @exception_dialogs
    def run():
        # show the setup dialog in which the user can first login and then choose the name of the database
        # and whether to import the accompanied biosphere, or connect to an existing biosphere
        setup = EiWizard(application.main_window)
        setup.exec_()


class EiWizard(widgets.ABWizard):
    class RemoteOrLocalPage(widgets.ABWizardPage):

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setTitle("Import from ecoinvent")
            self.setSubTitle("Choose whether to import from a remote or local ecoinvent release.")

            self.remote_button = QtWidgets.QRadioButton("Remote")
            self.local_button = QtWidgets.QRadioButton("Local")
            self.remote_button.setChecked(True)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.remote_button)
            layout.addWidget(self.local_button)
            self.setLayout(layout)

        def nextPage(self):
            if self.local_button.isChecked():
                return EiWizard.LocalSelectPage
            else:
                return EiWizard.LoginPage

    class LocalSelectPage(widgets.ABWizardPage):

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setTitle("Import from ecoinvent")
            self.setSubTitle("Select local ecoinvent .7z.")

            self.file_selector = widgets.ABFileSelector(filter="*.7z")
            self.file_selector.textChanged.connect(lambda: self.completeChanged.emit())

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.file_selector)
            self.setLayout(layout)

        def finalize(self, context: dict):
            context["ei_filepath"] = self.file_selector.text()

        def isComplete(self):
            return bool(self.file_selector.text())

        def nextPage(self):
            return EiWizard.BiosphereSetupPage

    class LoginPage(widgets.ABWizardPage):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Login")
            self.setSubTitle("Login with your ecoinvent credentials to authorize the download")

            self.release = None

            # create username field
            self.username = QtWidgets.QLineEdit()
            self.username.setPlaceholderText('ecoinvent username')

            # create password field and set hidden
            self.password = QtWidgets.QLineEdit()
            self.password.setPlaceholderText('ecoinvent password'),
            self.password.setEchoMode(QtWidgets.QLineEdit.Password)

            # empty message for now, will be used in case of wrong password or other error
            self.message = QtWidgets.QLabel()

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.username)
            layout.addWidget(self.password)
            layout.addWidget(self.message)

            self.setLayout(layout)

        def initializePage(self, context: dict):
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
                self.release = ei.EcoinventRelease(settings)
                self.release.list_versions()

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
            QtWidgets.QApplication.restoreOverrideCursor()
            return True

        def finalize(self, context: dict):
            context["release"] = self.release

        def nextPage(self):
            return EiWizard.EcoinventVersionPage

    class EcoinventVersionPage(widgets.ABWizardPage):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Choose version")
            self.setSubTitle("Choose ecoinvent version and system model")

            # set up the version & model comboboxes
            self.versions = QtWidgets.QComboBox()
            self.models = QtWidgets.QComboBox()

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.versions)
            layout.addWidget(self.models)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            self.release = context["release"]
            self.versions.currentTextChanged.connect(self.collect_models)
            self.versions.addItems(self.release.list_versions())

        def finalize(self, context: dict):
            context["version"] = self.versions.currentText()
            context["model"] = self.models.currentText()

        def nextPage(self):
            return EiWizard.EcoinventDownloadPage

        def collect_models(self, version: str):
            """Slot for when the version selection changes"""
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.models.clear()
            self.models.addItems(self.release.list_system_models(version))
            QtWidgets.QApplication.restoreOverrideCursor()

    class EcoinventDownloadPage(widgets.ABWizardPage):

        class DownloadThread(threading.ABThread):
            download_ready: SignalInstance = Signal(str)

            release = None
            version: str
            model: str

            def run_safely(self):
                print("starting download")
                path = self.release.get_release(
                    version=self.version,
                    system_model=self.model,
                    release_type=ei.ReleaseType.ecospold,
                    extract=False,
                    fix_version=False
                )

                path = str(path)

                if not path.endswith(".7z"):
                    path = path + ".7z"

                self.download_ready.emit(path)

        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Download ecoinvent")
            self.setSubTitle("Downloading the selected ecoinvent release")

            self.ei_filepath = None

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setRange(0, 0)
            self.download_thread = self.DownloadThread(application)

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.progress_bar)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            self.download_thread.release = context["release"]
            self.download_thread.version = context["version"]
            self.download_thread.model = context["model"]

            self.download_thread.start()
            self.download_thread.download_ready.connect(self.download_ready)

        def download_ready(self, filepath: str):
            self.ei_filepath = filepath

            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)

            self.completeChanged.emit()

        def finalize(self, context: dict):
            context["ei_filepath"] = self.ei_filepath

        def isComplete(self):
            return self.download_thread.isFinished()

        def nextPage(self):
            return EiWizard.BiosphereSetupPage

    class BiosphereSetupPage(widgets.ABWizardPage):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Biosphere setup")
            self.setSubTitle("Choose whether to import the biosphere database or connect to an existing one")

            self.biosphere_choice = widgets.ABRadioButtonCollapser(self)
            self.biosphere_choice.buttonClicked.connect(lambda: self.completeChanged.emit())

            # add option to connect to an existing biosphere database
            self.biosphere_choice.addOption(
                name="existing",
                label="Link to an existing biosphere",
                w=widgets.ABComboBox.get_database_combobox()
            )

            # add option to install the supplied biosphere database
            self.biosphere_choice.addOption(
                name="import",
                label="Import included biosphere",
                w=QtWidgets.QLineEdit("biosphere3")
            )

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.biosphere_choice)

            self.setLayout(layout)

        def isComplete(self):
            return self.biosphere_choice.currentOption() is not None

        def finalize(self, context: dict):
            if self.biosphere_choice.currentOption() == "existing":
                context["biosphere_name"] = self.biosphere_choice.view("existing").currentText()
            else:
                context["biosphere_name"] = self.biosphere_choice.view("import").text()

        def nextPage(self):
            if self.biosphere_choice.currentOption() == "existing":
                return EiWizard.EcoinventSetupPage
            else:
                return EiWizard.BiosphereInstallPage

    class BiosphereInstallPage(widgets.ABWizardPage):
        class InstallThread(threading.ABThread):
            ei_filepath: str
            biosphere_name: str

            def run_safely(self):
                importer = Ecoinvent7zImporter(self.ei_filepath)
                importer.install_biosphere(self.biosphere_name)

        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Installing biosphere database")
            self.setSubTitle("Installing bundled biosphere database into the project")

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setRange(0, 0)
            self.install_thread = self.InstallThread(application)

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.progress_bar)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            self.install_thread.ei_filepath = context["ei_filepath"]
            self.install_thread.biosphere_name = context["biosphere_name"]

            self.install_thread.start()
            self.install_thread.finished.connect(self.ready)

        def ready(self):
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)

            self.completeChanged.emit()

        def isComplete(self):
            return self.install_thread.isFinished()

        def nextPage(self):
            return EiWizard.MethodsSetupPage

    class MethodsSetupPage(widgets.ABWizardPage):
        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Methods setup")
            self.setSubTitle("Choose whether to import methods from eocoinvent or from file")

            self.methods_choice = widgets.ABRadioButtonCollapser(self)
            self.methods_choice.buttonClicked.connect(lambda: self.completeChanged.emit())

            # add option to connect to an existing methods database
            self.methods_choice.addOption(
                name="remote",
                label="Download methods from ecoinvent",
                w=QtWidgets.QWidget()
            )

            # add option to install the supplied methods database
            self.methods_choice.addOption(
                name="local",
                label="Import methods from file",
                w=widgets.ABFileSelector(filter="*.xlsx")
            )

            # add option to install the supplied methods database
            self.methods_choice.addOption(
                name="skip",
                label="Don't import methods",
                w=QtWidgets.QWidget()
            )

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.methods_choice)

            self.setLayout(layout)

        def finalize(self, context: dict):
            if self.methods_choice.currentOption() == "remote":
                file = ei.get_excel_lcia_file_for_version(context["release"], context["version"])
                context["methods_filepath"] = str(file)
            if self.methods_choice.currentOption() == "local":
                context["methods_filepath"] = self.methods_choice.view("local").text()

        def isComplete(self):
            return self.methods_choice.currentOption() is not None

        def nextPage(self):
            if self.methods_choice.currentOption() == "remote" or self.methods_choice.currentOption() == "local":
                return EiWizard.MethodsInstallPage
            else:
                return EiWizard.EcoinventSetupPage

    class MethodsInstallPage(widgets.ABWizardPage):
        class InstallThread(threading.ABThread):
            methods_filepath: str
            biosphere_name: str

            def run_safely(self):
                importer = EcoinventLCIAImporter.setup_with_ei_excel(self.methods_filepath)

                importer.set_biosphere(self.biosphere_name)
                importer.apply_strategies()

                signals.method.blockSignals(True)
                signals.meta.blockSignals(True)
                old = bd.methods.deserialize()

                importer.write_methods(overwrite=True)

                signals.method.blockSignals(False)
                signals.meta.blockSignals(False)
                signals.meta.methods_changed.emit(deepcopy(bd.methods.data), old)

        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Methods import")
            self.setSubTitle("Importing methods and linking to biosphere")

            self.methods_choice = widgets.ABRadioButtonCollapser(self)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setRange(0, 0)
            self.install_thread = self.InstallThread(application)

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.progress_bar)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            self.install_thread.methods_filepath = context["methods_filepath"]
            self.install_thread.biosphere_name = context["biosphere_name"]

            self.install_thread.start()
            self.install_thread.finished.connect(self.ready)

        def ready(self):
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)

            self.completeChanged.emit()

        def isComplete(self):
            return self.install_thread.isFinished()

        def nextPage(self):
            return EiWizard.EcoinventSetupPage

    class EcoinventSetupPage(widgets.ABWizardPage):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setTitle("ecoinvent setup")
            self.setSubTitle("Choose name for ecoinvent database")

            self.database_name = QtWidgets.QLineEdit()
            self.database_name.textChanged.connect(lambda: self.completeChanged.emit())

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.database_name)
            self.setLayout(layout)

        def isComplete(self):
            return bool(self.database_name.text())

        def finalize(self, context: dict):
            context["database_name"] = self.database_name.text()

        def nextPage(self):
            return EiWizard.EcoinventInstallPage

    class EcoinventInstallPage(widgets.ABWizardPage):
        class InstallThread(threading.ABThread):
            def run_safely(self, ei_filepath: str, database_name: str, biosphere_name: str):
                importer = Ecoinvent7zImporter(ei_filepath)
                importer.install_ecoinvent(database_name, biosphere_name)

        def __init__(self, parent=None):
            super().__init__(parent)

            self.setTitle("Ecoinvent installation")
            self.setSubTitle("Installing ecoinvent database")
            self.setFinalPage(True)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setRange(0, 0)
            self.install_thread = self.InstallThread(application)

            # set layout
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.progress_bar)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            self.install_thread.start(
                context["ei_filepath"],
                context["database_name"],
                context["biosphere_name"]
            )
            self.install_thread.finished.connect(self.ready)

        def ready(self):
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)

            self.completeChanged.emit()

        def isComplete(self):
            return self.install_thread.isFinished()

    pages = [
        RemoteOrLocalPage, LocalSelectPage, LoginPage, EcoinventVersionPage, EcoinventDownloadPage, BiosphereSetupPage,
        BiosphereInstallPage, MethodsSetupPage, MethodsInstallPage, EcoinventSetupPage, EcoinventInstallPage
    ]
