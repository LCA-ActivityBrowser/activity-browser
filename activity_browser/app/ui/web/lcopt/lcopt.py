# -*- coding: utf-8 -*-
import os

import requests
import lcopt
from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets


LCOPT_URL = 'http://127.0.0.1:5000/'


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

        # load options
        self.create_edit = QtWidgets.QLineEdit()
        self.create_edit.setPlaceholderText('name of new model')
        self.create_button = QtWidgets.QPushButton('Create Model')
        self.create_button.setEnabled(False)
        self.load_combobox = QtWidgets.QComboBox()
        self.load_button = QtWidgets.QPushButton('Load Model')
        self.example_combobox = QtWidgets.QComboBox()
        self.example_button = QtWidgets.QPushButton('Load Example')

        # layout
        self.create_gb = OptionGroupBox('Create a new model', self.create_edit,
                                        self.create_button)
        self.load_gb = OptionGroupBox('Load an existing model', self.load_combobox,
                                      self.load_button)
        self.example_gb = OptionGroupBox('Load an example model', self.example_combobox,
                                         self.example_button)

        self.option_layout = QtWidgets.QHBoxLayout()
        self.option_layout.addStretch()
        self.option_layout.addWidget(self.create_gb)
        self.option_layout.addWidget(self.load_gb)
        self.option_layout.addWidget(self.example_gb)
        self.option_layout.addStretch()
        self.option_widget = QtWidgets.QWidget()  # needed for setVisible
        self.option_widget.setLayout(self.option_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.option_widget)
        self.layout.addWidget(self.view)
        self.layout.setStretchFactor(self.view, 100)
        self.layout.addStretch()
        self.setLayout(self.layout)

        # view
        self.url = QtCore.QUrl(LCOPT_URL)

        self.connect_signals()
        self.update_options()

    def connect_signals(self):
        lcopt_signals.app_running.connect(self.reload)
        self.create_edit.textEdited.connect(self.update_create)
        self.create_button.clicked.connect(self.create_model)
        self.load_button.clicked.connect(self.load_model)
        self.example_button.clicked.connect(self.load_example)
        lcopt_signals.app_running.connect(self.switch_options_view)
        lcopt_signals.app_shutdown.connect(self.switch_options_view)

    def switch_options_view(self):
        self.view.setVisible(not self.view.isVisible())
        self.option_widget.setVisible(not self.option_widget.isVisible())
        self.update_options()

    def update_options(self):
        self.models = [m for m in os.listdir('.') if m.endswith('.lcopt')]
        self.model_dict = {m: os.path.join(os.path.abspath('.'), m) for m in self.models}
        self.load_combobox.clear()
        self.load_combobox.addItems(self.models)
        self.load_gb.setEnabled(bool(self.models))
        self.example_combobox.clear()
        self.example_combobox.addItems(['ecoinvent_example.lcopt'])  # TODO: include forwast

    def reload(self):
        self.view.load(self.url)
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

    def run_lcopt(self, model):
        self.lcopt_thread = LcoptThread(model)
        self.reload_helper_thread = ReloadHelperThread()
        self.reload_helper_thread.start()
        self.lcopt_thread.start()

    def create_model(self):
        model_name = self.create_edit.text()
        model = lcopt.LcoptModel(model_name)
        self.run_lcopt(model)

    def load_model(self):
        model_name = self.load_combobox.currentText()
        model_path = self.model_dict[model_name]
        model = lcopt.LcoptModel(load=model_path)
        self.run_lcopt(model)

    def load_example(self):
        lcopt_asset_path = os.path.join(lcopt.__path__[0], 'assets')
        model_name = self.example_combobox.currentText()
        ecoinvent_example = os.path.join(lcopt_asset_path, model_name)
        model = lcopt.LcoptModel(load=ecoinvent_example)
        self.run_lcopt(model)


class OptionGroupBox(QtWidgets.QGroupBox):
    def __init__(self, title, option, button):
        super().__init__(title)
        self.lay = QtWidgets.QVBoxLayout()
        self.lay.addWidget(option)
        self.lay.addWidget(button)
        self.setLayout(self.lay)


class LcoptThread(QtCore.QThread):
    """
    lcopt flask app must run in its own thread, because it's blocking
    """
    def __init__(self, model):
        super().__init__()
        self.model = model

    def run(self):
        my_flask = ABFlaskSandbox(self.model)
        my_flask.run()
        self.quit()


class ReloadHelperThread(QtCore.QThread):
    """
    this helper thread checks if lcopt is ready and sends the signal to update the ui,
    otherwise the "browser" shows a connection error and the user must manually reload the page
    """
    def run(self):
        while True:
            try:
                requests.get(LCOPT_URL)
                lcopt_signals.app_running.emit()
                break
            except requests.ConnectionError:
                print('.', end='')
            self.msleep(10)
        self.quit()


class ABFlaskSandbox(lcopt.interact.FlaskSandbox):
    """
    subclassing the lcopt FlaskSandbox to not open a browser in addition to the AB
    """
    def run(self):
        app = self.create_app()
        app.run()

    def shutdown_server(self):
        super().shutdown_server()
        lcopt_signals.app_shutdown.emit()


class LcoptSignals(QtCore.QObject):
    """
    lcopt-specific signals to communicate between the threads
    """
    app_running = QtCore.pyqtSignal()
    app_shutdown = QtCore.pyqtSignal()


lcopt_signals = LcoptSignals()
