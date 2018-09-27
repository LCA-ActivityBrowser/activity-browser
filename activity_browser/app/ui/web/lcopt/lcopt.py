# -*- coding: utf-8 -*-
import os

import requests
import lcopt
from lcopt.settings_gui import FlaskSettingsGUI
import brightway2 as bw
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets

from activity_browser.app.ui.wizards.db_import_wizard import (
    DatabaseImportWizard,
    EcoinventLoginPage,
    ConfirmationPage,
    ImportPage
)
from ....signals import signals
from activity_browser.app.ui.wizards.db_import_wizard import import_signals


class LcoptWidget(QtWidgets.QWidget):
    """
    LcoptWidget displays the options to create/load an lcopt model and displays the flask app
    top-level full-app window like the main window and the sankey window
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = "&LCOPT"
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.setVisible(False)

        # lcopt config
        if lcopt.settings.model_storage.project != 'single':
            lcopt.settings.model_storage.project = 'single'
            print('Changed lcopt model storage to single project!')
            # TODO: add option to disable this or revert to user config when AB is closed
            # or just ask for user confirmation
        lcopt_single_project = lcopt.storage.single_project_name
        if lcopt_single_project not in bw.projects:
            bw.projects.create_project(lcopt_single_project)
        signals.change_project.emit(lcopt_single_project)
        if 'biosphere3' not in bw.databases:
            signals.install_default_data.emit()

        # settings/setup options
        self.lcopt_settings_button = QtWidgets.QPushButton('Lcopt Settings')
        self.ecoinvent_setup_button = QtWidgets.QPushButton('Setup LCOPT with Ecoinvent')
        self.forwast_setup_button = QtWidgets.QPushButton('Setup LCOPT with Forwast')
        self.forwast_setup_button.setEnabled(False)

        # load options
        self.create_edit = QtWidgets.QLineEdit()
        self.create_edit.setPlaceholderText('name of new model')
        self.create_button = QtWidgets.QPushButton('Create Model')
        self.create_button.setEnabled(False)
        self.load_combobox = QtWidgets.QComboBox()
        self.load_button = QtWidgets.QPushButton('Load Model')

        # return to main window
        self.close_button = QtWidgets.QPushButton('Return to Main Window')

        # layout
        self.setup_gb = OptionGroupBox(
            'Setup/Settings', self.ecoinvent_setup_button, self.forwast_setup_button
        )
        self.setup_gb.lay.addWidget(self.lcopt_settings_button)
        self.create_gb = OptionGroupBox('Create a new model', self.create_edit,
                                        self.create_button)
        self.load_gb = OptionGroupBox('Load an existing model', self.load_combobox,
                                      self.load_button)

        self.option_layout = QtWidgets.QHBoxLayout()
        self.option_layout.addStretch()
        self.option_layout.setAlignment(self.lcopt_settings_button, QtCore.Qt.AlignTop)
        self.option_layout.addWidget(self.setup_gb)
        self.option_layout.addWidget(self.create_gb)
        self.option_layout.addWidget(self.load_gb)
        self.option_layout.addStretch()
        self.option_layout.addWidget(self.close_button)
        self.option_layout.setAlignment(self.close_button, QtCore.Qt.AlignTop)
        self.option_widget = QtWidgets.QWidget()  # needed for setVisible
        self.option_widget.setLayout(self.option_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.option_widget)
        self.layout.addWidget(self.view)
        self.layout.setStretchFactor(self.view, 100)
        self.layout.addStretch()
        self.setLayout(self.layout)

        # view
        self.url = 'http://127.0.0.1:5000'

        self.connect_signals()
        self.update_options()

    def connect_signals(self):
        lcopt_signals.app_running.connect(self.reload)
        self.create_edit.textEdited.connect(self.update_create)
        self.create_button.clicked.connect(self.create_model)
        self.load_button.clicked.connect(self.load_model)
        lcopt_signals.app_running.connect(self.switch_options_view)
        lcopt_signals.app_shutdown.connect(self.switch_options_view)
        lcopt_signals.app_shutdown.connect(self.global_updates)
        self.close_button.clicked.connect(self.return_main_window)
        self.lcopt_settings_button.clicked.connect(self.run_lcopt)
        lcopt_signals.model_ready.connect(self.run_model)

    def switch_options_view(self):
        self.view.setVisible(not self.view.isVisible())
        self.option_widget.setVisible(not self.option_widget.isVisible())
        self.update_options()

    def update_options(self):
        self.models = {os.path.split(m)[1].replace('.lcopt', ''): m for m in lcopt.storage.models}
        self.load_combobox.clear()
        self.load_combobox.addItems(sorted(self.models))
        self.load_gb.setEnabled(bool(self.models))

    def reload(self):
        self.view.load(QtCore.QUrl(self.url))
        print('reloading')

    def update_create(self):
        valid = self.valid_model_name()
        self.create_button.setEnabled(valid)
        # code below (dis)connects the returnPressed signal to avoid empty/taken modelnames
        if valid:
            if not self.create_edit.receivers(self.create_edit.returnPressed):
                self.create_edit.returnPressed.connect(self.create_model)
        else:
            self.create_edit.returnPressed.disconnect()

    def valid_model_name(self):
        name = self.create_edit.text()
        model_names = [m.replace('.lcopt', '') for m in self.models]
        valid = bool(name) and name not in model_names
        return valid

    def run_lcopt(self, *args, model=None):
        self.lcopt_port = lcopt.utils.find_port()
        self.url = 'http://127.0.0.1:{}/'.format(self.lcopt_port)
        self.lcopt_thread = LcoptThread(model, self.lcopt_port)
        self.reload_helper_thread = ReloadHelperThread(self.url)
        self.reload_helper_thread.start()
        self.lcopt_thread.start()

    def create_model(self):
        model_name = self.create_edit.text()
        self.model = lcopt.LcoptModel(model_name, ei_setup=self.ab_ei_setup)
        if not hasattr(self, 'setup_wizard'):
            lcopt_signals.model_ready.emit()

    def load_model(self):
        model_name = self.load_combobox.currentText()
        model_path = self.models[model_name]
        self.model = lcopt.LcoptModel(load=model_path, ei_setup=self.ab_ei_setup)
        if not hasattr(self, 'setup_wizard'):
            lcopt_signals.model_ready.emit()

    def run_model(self):
        self.run_lcopt(model=self.model)

    def return_main_window(self):
        window = self.window()
        window.stacked.setCurrentWidget(window.main_widget)

    def global_updates(self):
        signals.projects_changed.emit()
        signals.databases_changed.emit()

    def ab_ei_setup(self, **kwargs):
        print(f'kwargs:\n{kwargs}')
        version = kwargs['ecoinvent_version']
        system_model = kwargs['ecoinvent_system_model']
        print('ask for confirmation to start setup here')
        ei_name = "Ecoinvent{}_{}_{}".format(*version.split('.'), system_model)
        if ei_name in bw.databases and not kwargs['overwrite']:
            if hasattr(self, 'setup_wizard'):
                del self.setup_wizard
        else:
            self.setup_wizard = LcoptSetupWizard(version=version, system_model=system_model)


class OptionGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title, option, button):
        super().__init__(title)
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.addWidget(option)
        self.lay.addWidget(button)
        self.setLayout(self.lay)


class LcoptSetupWizard(DatabaseImportWizard):
    def __init__(self, version=None, system_model=None):
        self._version = version
        self._system_model = system_model
        super().__init__()
        self.update_downloader()
        # fake_line_edit only needed to register db_name field
        self.confirmation_page.fake_line_edit = QtWidgets.QLineEdit()
        self.confirmation_page.fake_line_edit2 = QtWidgets.QLineEdit()
        self.confirmation_page.registerField('db_name', self.confirmation_page.fake_line_edit)
        ei_name = "Ecoinvent{}_{}_{}".format(*self.version.split('.'), self.system_model)
        self.setField('db_name', ei_name)   # following the lcopt naming convention

        self.determine_import_type()
        import_signals.finished.connect(self.emit_model_ready)

    def determine_import_type(self):
        if self.downloader.check_stored():
            self.import_type = 'archive'
            self.confirmation_page.registerField(
                'archive_path', self.confirmation_page.fake_line_edit2
            )
            self.setField('archive_path', self.downloader.out_path)
            import_signals.login_success.emit(True)
        else:
            self.import_type = 'homepage'
        print(self.import_type)

    def add_pages(self):
        self.ecoinvent_login_page = EcoinventLoginPage(self)
        self.confirmation_page = ConfirmationPage(self)
        self.import_page = ImportPage(self)
        self.pages = [
            self.ecoinvent_login_page,
            self.confirmation_page,
            self.import_page
        ]
        for page in self.pages:
            self.addPage(page)

    @property
    def version(self):
        if self._version is None:
            return lcopt.settings.ecoinvent.version
        else:
            return self._version

    @property
    def system_model(self):
        if self._system_model is None:
            return lcopt.settings.ecoinvent.system_model
        else:
            return self._system_model

    def emit_model_ready(self):
        lcopt_signals.model_ready.emit()


class LcoptThread(QtCore.QThread):
    """
    lcopt flask app must run in its own thread, because it's blocking
    runs the settings gui if no model is provided
    """
    def __init__(self, model, port):
        super().__init__()
        self.port = port
        self.model = model

    def run(self):
        if self.model is None:
            my_flask = ABFlaskSettingsGui()
        else:
            my_flask = ABFlaskSandbox(self.model)
        my_flask.run(port=self.port, open_browser=False)
        self.quit()


class ReloadHelperThread(QtCore.QThread):
    """
    this helper thread checks if lcopt is ready and sends the signal to update the ui,
    otherwise the "browser" shows a connection error and the user must manually reload the page
    """
    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        while True:
            try:
                requests.get(self.url)
                lcopt_signals.app_running.emit()
                break
            except requests.ConnectionError:
                print('.', end='')
            self.msleep(10)
        self.quit()


class ABFlaskSandbox(lcopt.interact.FlaskSandbox):
    """
    subclassing the lcopt FlaskSandbox to be able to emit shutdown signal
    """
    def shutdown_server(self):
        super().shutdown_server()
        lcopt_signals.app_shutdown.emit()


class ABFlaskSettingsGui(FlaskSettingsGUI):
    def shutdown_server(self):
        super().shutdown_server()
        lcopt_signals.app_shutdown.emit()


class LcoptSignals(QtCore.QObject):
    """
    lcopt-specific signals to communicate between the threads
    """
    app_running = QtCore.pyqtSignal()
    app_shutdown = QtCore.pyqtSignal()
    model_ready = QtCore.pyqtSignal()


lcopt_signals = LcoptSignals()
