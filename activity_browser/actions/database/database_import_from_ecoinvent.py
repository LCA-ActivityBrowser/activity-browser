import re
from logging import getLogger
from copy import deepcopy

import requests

import ecoinvent_interface as ei
import bw2data as bd
import bw2io as bi

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import application, signals
from activity_browser.ui import widgets, icons, threading
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.io.ecoinvent_importer import Ecoinvent7zImporter
from activity_browser.bwutils.io.ecoinvent_lcia_importer import EcoinventLCIAImporter
from activity_browser.mod.bw2io.migrations import ab_create_core_migrations

log = getLogger(__name__)


class DatabaseImportFromEcoinvent(ABAction):
    """
    Launches the `EiWizard` dialog for importing a database from ecoinvent.

    This method creates an instance of the `EiWizard` class, passing the
    main application window as its parent, and executes the wizard dialog.

    Raises:
        Any exceptions encountered during the execution of the wizard
        are handled by the `exception_dialogs` decorator.
    """

    icon = icons.qicons.import_db
    text = "Import database from ecoinvent"
    tool_tip = "Import database from ecoinvent"

    @staticmethod
    @exception_dialogs
    def run():
        setup = EiWizard(application.main_window)
        setup.setWindowTitle("Import from ecoinvent")
        setup.exec_()


class EiWizard(widgets.ABWizard):
    """Wizard for importing database from ecoinvent"""

    class RemoteOrLocalPage(widgets.ABWizardPage):
        """Wizard page to choose between remote or local ecoinvent release"""
        title = "Import from ecoinvent"
        subtitle = "Choose whether to import from a remote or local ecoinvent release."

        def __init__(self, parent=None):
            super().__init__(parent)

            self.remote_button = QtWidgets.QRadioButton("Remote")
            self.local_button = QtWidgets.QRadioButton("Local")
            self.remote_button.setChecked(True)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.remote_button)
            layout.addWidget(self.local_button)
            self.setLayout(layout)

        def nextPage(self):
            """Determine the next page based on the user's selection"""
            if self.local_button.isChecked():
                return EiWizard.LocalSelectPage
            else:
                return EiWizard.LoginPage

    class LocalSelectPage(widgets.ABWizardPage):
        """Wizard page to select a local ecoinvent .7z file"""
        title = "Import from ecoinvent"
        subtitle = "Select local ecoinvent .7z."

        def __init__(self, parent=None):
            super().__init__(parent)

            self.file_selector = widgets.ABFileSelector(filter="*.7z")
            self.file_selector.textChanged.connect(lambda: self.completeChanged.emit())

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.file_selector)
            self.setLayout(layout)

        def finalize(self, context: dict):
            """Store the selected file path in the context"""
            path = self.file_selector.text()
            context["ei_filepath"] = path
            # Try to extract version and model from the filename
            if version:= re.search(r'ecoinvent ([\d.]+)', path):
                context["version"] = version.group(1)
            if model:= re.search(r'ecoinvent [\d.]+_([^_]+)', path):
                context["model"] = model.group(1)

        def isComplete(self):
            """Check if a file has been selected"""
            return bool(self.file_selector.text())

        def nextPage(self):
            """Proceed to the BiosphereSetupPage"""
            return EiWizard.BiosphereSetupPage

    class LoginPage(widgets.ABWizardPage):
        """Wizard page to login with ecoinvent credentials"""
        title = "Login"
        subtitle = "Login with your ecoinvent credentials to authorize the download"

        def __init__(self, parent=None):
            super().__init__(parent)

            self.release = None

            self.username = QtWidgets.QLineEdit()
            self.username.setPlaceholderText('ecoinvent username')

            self.password = QtWidgets.QLineEdit()
            self.password.setPlaceholderText('ecoinvent password')
            self.password.setEchoMode(QtWidgets.QLineEdit.Password)

            self.message = QtWidgets.QLabel()

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.username)
            layout.addWidget(self.password)
            layout.addWidget(self.message)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            """Initialize the page with stored username and password"""
            settings = ei.Settings()
            self.username.setText(settings.username)
            self.password.setText(settings.password)

        def validatePage(self):
            """Validate the login credentials by attempting to list ecoinvent versions"""
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                settings = ei.Settings(username=self.username.text(), password=self.password.text())
                self.release = ei.EcoinventRelease(settings)
                self.release.list_versions()
            except requests.exceptions.HTTPError as e:
                QtWidgets.QApplication.restoreOverrideCursor()
                if e.response.status_code == 401:
                    self.message.setText("Invalid username and/or password, please try again.")
                    return False
                else:
                    self.message.setText("Unknown connection error, try again later.")
                    raise e
            ei.permanent_setting("username", self.username.text())
            ei.permanent_setting("password", self.password.text())
            QtWidgets.QApplication.restoreOverrideCursor()
            return True

        def finalize(self, context: dict):
            """Store the release object in the context"""
            context["release"] = self.release

        def nextPage(self):
            """Proceed to the EcoinventVersionPage"""
            return EiWizard.EcoinventVersionPage

    class EcoinventVersionPage(widgets.ABWizardPage):
        """Wizard page to choose ecoinvent version and system model"""
        title = "Choose version"
        subtitle = "Choose ecoinvent version and system model"

        def __init__(self, parent=None):
            super().__init__(parent)

            self.versions = QtWidgets.QComboBox()
            self.models = QtWidgets.QComboBox()

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.versions)
            layout.addWidget(self.models)

            self.setLayout(layout)

        def initializePage(self, context: dict):
            """Initialize the page with available versions and models"""
            self.release = context["release"]
            self.versions.currentTextChanged.connect(self.collect_models)
            self.versions.addItems(self.release.list_versions())

        def finalize(self, context: dict):
            """Store the selected version and model in the context"""
            context["version"] = self.versions.currentText()
            context["model"] = self.models.currentText()

        def nextPage(self):
            """Proceed to the EcoinventDownloadPage"""
            return EiWizard.EcoinventDownloadPage

        def collect_models(self, version: str):
            """Collect and display system models for the selected version"""
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.models.clear()
            self.models.addItems(self.release.list_system_models(version))
            QtWidgets.QApplication.restoreOverrideCursor()

    class EcoinventDownloadPage(widgets.ABThreadedWizardPage):
        """Wizard page to download the selected ecoinvent release"""
        title = "Download ecoinvent"
        subtitle = "Downloading the selected ecoinvent release"

        class Thread(threading.ABThread):
            """Thread to handle the download process"""
            download_ready: SignalInstance = Signal(str)

            def run_safely(self, release: ei.release, version: str, model: str):
                """Download the ecoinvent release"""
                path = release.get_release(
                    version=version,
                    system_model=model,
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
            self.ei_filepath = None

        def initializePage(self, context: dict):
            """Start the download thread"""
            self.thread.start(context["release"], context["version"], context["model"])
            self.thread.download_ready.connect(self.download_ready)

        def download_ready(self, filepath: str):
            """Handle the completion of the download"""
            self.ei_filepath = filepath

        def finalize(self, context: dict):
            """Store the downloaded file path in the context"""
            context["ei_filepath"] = self.ei_filepath

        def nextPage(self):
            """Proceed to the BiosphereSetupPage"""
            return EiWizard.BiosphereSetupPage

    class BiosphereSetupPage(widgets.ABWizardPage):
        """Wizard page to choose biosphere setup options"""
        title = "Biosphere setup"
        subtitle = "Choose whether to import the biosphere database or connect to an existing one"

        def __init__(self, parent=None):
            super().__init__(parent)

            self.biosphere_choice = widgets.ABRadioButtonCollapser(self)
            self.biosphere_choice.buttonClicked.connect(lambda: self.completeChanged.emit())

            self.biosphere_choice.addOption(
                name="existing",
                label="Link to an existing biosphere",
                w=widgets.ABComboBox.get_database_combobox()
            )

            self.biosphere_choice.addOption(
                name="import",
                label="Import included biosphere",
                w=widgets.DatabaseNameEdit(database_preset="biosphere")
            )

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.biosphere_choice)
            self.setLayout(layout)

        def isComplete(self):
            """Check if a biosphere option has been selected"""
            return self.biosphere_choice.currentOption() is not None

        def initializePage(self, context: dict):
            """Start the biosphere installation thread"""
            if "version" in context:
                self.biosphere_choice.view("import").setText(f"biosphere-{context['version']}")

        def finalize(self, context: dict):
            """Store the selected biosphere option in the context"""
            if self.biosphere_choice.currentOption() == "existing":
                context["biosphere_name"] = self.biosphere_choice.view("existing").currentText()
            else:
                context["biosphere_name"] = self.biosphere_choice.view("import").text()

        def nextPage(self):
            """Proceed to the appropriate next page based on the biosphere choice"""
            if self.biosphere_choice.currentOption() == "existing":
                return EiWizard.EcoinventSetupPage
            else:
                return EiWizard.BiosphereInstallPage

    class BiosphereInstallPage(widgets.ABThreadedWizardPage):
        """Wizard page to install the biosphere database"""
        title = "Installing biosphere database"
        subtitle = "Installing bundled biosphere database into the project"

        class Thread(threading.ABThread):
            """Thread to handle the biosphere installation process"""
            def run_safely(self, ei_filepath: str, biosphere_name: str):
                """Install the biosphere database"""
                importer = Ecoinvent7zImporter(ei_filepath)
                importer.install_biosphere(biosphere_name)

        def initializePage(self, context: dict):
            """Start the biosphere installation thread"""
            self.thread.start(context["ei_filepath"], context["biosphere_name"])

        def nextPage(self):
            """Proceed to the MethodsSetupPage"""
            return EiWizard.MethodsSetupPage

    class MethodsSetupPage(widgets.ABWizardPage):
        """Wizard page to choose methods setup options"""
        title = "Methods setup"
        subtitle = "Choose whether to import methods from ecoinvent or from file"

        def __init__(self, parent=None):
            super().__init__(parent)

            self.methods_choice = widgets.ABRadioButtonCollapser(self)
            self.methods_choice.buttonClicked.connect(lambda: self.completeChanged.emit())

            self.methods_choice.addOption(
                name="remote",
                label="Download methods from ecoinvent",
                w=QtWidgets.QWidget()
            )

            self.methods_choice.addOption(
                name="local",
                label="Import methods from file",
                w=widgets.ABFileSelector(filter="*.xlsx")
            )

            self.methods_choice.addOption(
                name="skip",
                label="Don't import methods",
                w=QtWidgets.QWidget()
            )

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.methods_choice)

            self.setLayout(layout)

        def finalize(self, context: dict):
            """Store the selected methods option in the context"""
            if self.methods_choice.currentOption() == "remote":
                file = ei.get_excel_lcia_file_for_version(context["release"], context["version"])
                context["methods_filepath"] = str(file)
            if self.methods_choice.currentOption() == "local":
                context["methods_filepath"] = self.methods_choice.view("local").text()

        def isComplete(self):
            """Check if a methods option has been selected"""
            return self.methods_choice.currentOption() is not None

        def nextPage(self):
            """Proceed to the appropriate next page based on the methods choice"""
            if self.methods_choice.currentOption() == "remote" or self.methods_choice.currentOption() == "local":
                return EiWizard.MethodsInstallPage
            else:
                return EiWizard.EcoinventSetupPage

    class MethodsInstallPage(widgets.ABThreadedWizardPage):
        """Wizard page to install the selected methods"""
        title = "Installing methods"
        subtitle = "Installing selected methods and linking to the biosphere"

        class Thread(threading.ABThread):
            """Thread to handle the methods installation process"""
            def run_safely(self, methods_filepath: str, biosphere_name: str):
                """Install the methods and link to the biosphere"""
                importer = EcoinventLCIAImporter.setup_with_ei_excel(methods_filepath)
                importer.set_biosphere(biosphere_name)
                importer.apply_strategies()

                signals.method.blockSignals(True)
                signals.meta.blockSignals(True)

                old = bd.methods.deserialize()
                importer.write_methods(overwrite=True)

                signals.method.blockSignals(False)
                signals.meta.blockSignals(False)

                signals.meta.methods_changed.emit(deepcopy(bd.methods.data), old)

        def initializePage(self, context: dict):
            """Start the methods installation thread"""
            self.thread.start(context["methods_filepath"], context["biosphere_name"])

        def nextPage(self):
            """Proceed to the EcoinventSetupPage"""
            return EiWizard.EcoinventSetupPage

    class EcoinventSetupPage(widgets.ABWizardPage):
        """Wizard page to set up the ecoinvent database"""
        title = "Ecoinvent setup"
        subtitle = "Choose name for ecoinvent database"

        def __init__(self, parent=None):
            super().__init__(parent)
            self.database_name = widgets.DatabaseNameEdit(database_preset="ecoinvent")
            self.database_name.textChanged.connect(self.completeChanged)

            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.database_name)
            self.setLayout(layout)

        def isComplete(self):
            """Check if a database name has been entered"""
            return bool(self.database_name.text())

        def initializePage(self, context: dict):
            """Start the biosphere installation thread"""
            if "version" in context and "model" in context:
                self.database_name.setText(f"ecoinvent-{context['version']}-{context['model']}")

        def finalize(self, context: dict):
            """Store the database name in the context"""
            context["database_name"] = self.database_name.text()

        def nextPage(self):
            """Proceed to the EcoinventInstallPage"""
            return EiWizard.EcoinventInstallPage

    class EcoinventInstallPage(widgets.ABThreadedWizardPage):
        """Wizard page to install the ecoinvent database"""
        title = "Installing ecoinvent"
        subtitle = "Installing ecoinvent database into the project"

        class Thread(threading.ABThread):
            """Thread to handle the ecoinvent installation process"""
            def run_safely(self, ei_filepath: str, database_name: str, biosphere_name: str):
                """Install the ecoinvent database"""
                importer = Ecoinvent7zImporter(ei_filepath)
                importer.install_ecoinvent(database_name, biosphere_name)

                # Run migrations after installation
                if len(bi.migrations) == 0:
                    ab_create_core_migrations()

        def initializePage(self, context: dict):
            """Start the ecoinvent installation thread"""
            self.thread.start(
                context["ei_filepath"],
                context["database_name"],
                context["biosphere_name"]
            )

    pages = [
        RemoteOrLocalPage, LocalSelectPage, LoginPage, EcoinventVersionPage, EcoinventDownloadPage, BiosphereSetupPage,
        BiosphereInstallPage, MethodsSetupPage, MethodsInstallPage, EcoinventSetupPage, EcoinventInstallPage
    ]
