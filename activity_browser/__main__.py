import sys
import os
from logging import getLogger
from importlib import metadata

import requests

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

from activity_browser import application
from activity_browser.ui import icons

from .logger import setup_ab_logging
from .static.icons import main

log = getLogger(__name__)


class SpecialProgressBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 10)

        self.going = "right"

        self.inner = QtWidgets.QFrame(self)
        self.inner.setFixedSize(502, 10)
        self.inner.setStyleSheet("background-color: #0070c0;")
        self.inner.move(100, 0)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.loop)
        self.timer.start(1)

    def loop(self):
        x = self.inner.x()

        if self.going == "right":
            x += 1
            if x > 500:
                self.going = "left"
                self.inner.setStyleSheet("background-color: #c00000;")
        elif self.going == "left":
            x -= 1
            if x < -500:
                self.going = "right"
                self.inner.setStyleSheet("background-color: #0070c0;")

        self.inner.move(x, 0)


class ABLoader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowTitle("Activity Browser Launcher")
        self.setFixedSize(500, 300)

        logo_pixmap = QtGui.QPixmap(os.path.join(main.__path__[0], "activitybrowser.png")).scaledToHeight(200, mode=Qt.TransformationMode.SmoothTransformation)
        logo_label = QtWidgets.QLabel(self)
        logo_label.setPixmap(logo_pixmap)

        self.text_label = QtWidgets.QLabel("Initializing", self)
        self.text_label.setContentsMargins(0, 0, 30, 0)

        loading_bar = SpecialProgressBar(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.text_label, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(loading_bar)
        layout.setContentsMargins(0, 35, 0, 0)

        self.setLayout(layout)

        self.load_modules()

    def load_modules(self):
        thread = ModuleThread(self)
        thread.finished.connect(self.load_layout)
        thread.status.connect(self.text_label.setText)
        thread.start()

    def load_layout(self):
        from .ui.widgets import MainWindow, CentralTabWidget
        from .layouts import panes, pages
        from activity_browser.bwutils import AB_metadata
        from activity_browser import signals

        application.main_window = MainWindow()
        central_widget = CentralTabWidget(application.main_window)
        central_widget.addTab(pages.WelcomePage(), "Welcome")
        central_widget.addTab(pages.ParametersPage(), "Parameters")

        application.main_window.setCentralWidget(central_widget)

        self.load_settings()

    def load_settings(self):
        self.text_label.setText("Loading project")
        thread = SettingsThread(self)
        thread.finished.connect(self.load_finished)
        thread.start()

    def load_finished(self):
        application.main_window.sync()
        application.main_window.show()
        self.deleteLater()


class ModuleThread(QtCore.QThread):
    status: QtCore.SignalInstance = QtCore.Signal(str)

    def run(self):
        self.status.emit("Loading Numpy")
        log.debug("ABLoader: Importing numpy")
        import numpy, pandas
        self.status.emit("Loading Brightway25")
        log.debug("ABLoader: Importing brightway modules")
        import bw2data, bw2calc, bw2analyzer, bw2io, bw_functional, bw_processing, matrix_utils
        self.status.emit("Loading Activity Browser")
        log.debug("ABLoader: Importing activity_browser")
        from activity_browser import actions, layouts, mod, settings, ui, signals
        from activity_browser.layouts import panes, pages
        from activity_browser.ui import core, widgets, web, wizards


class SettingsThread(QtCore.QThread):
    def run(self):
        import bw2data as bd
        from activity_browser import settings, actions

        if settings.ab_settings.settings:
            from pathlib import Path

            base_dir = Path(settings.ab_settings.current_bw_dir)
            project_name = settings.ab_settings.startup_project
            bd.projects.change_base_directories(base_dir, project_name=project_name, update=False)

        if not bd.projects.twofive:
            log.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
            actions.ProjectSwitch.set_warning_bar()

        log.info(f"Brightway2 data directory: {bd.projects._base_data_dir}")
        log.info(f"Brightway2 current project: {bd.projects.current}")


def run_activity_browser():
    pre_flight_checks()
    setup_ab_logging()
    loader = ABLoader()
    loader.show()
    application.set_icon()  # setting this here seems to fix the icon not showing sometimes
    sys.exit(application.exec_())


def run_activity_browser_no_launcher():
    pre_flight_checks()
    setup_ab_logging()

    modules = ModuleThread()
    modules.run()

    from .ui.widgets import MainWindow, CentralTabWidget
    from .layouts import panes, pages
    from activity_browser.bwutils import AB_metadata
    from activity_browser import signals

    application.main_window = MainWindow()
    central_widget = CentralTabWidget(application.main_window)
    central_widget.addTab(pages.WelcomePage(), "Welcome")
    central_widget.addTab(pages.ParametersPage(), "Parameters")

    application.main_window.setCentralWidget(central_widget)

    settings = SettingsThread()
    settings.run()

    application.main_window.sync()
    application.main_window.show()

    application.set_icon()  # setting this here seems to fix the icon not showing sometimes
    sys.exit(application.exec_())


def pre_flight_checks():

    if "--no-checks" in sys.argv:
        return

    check_pyside_version()

    if "CONDA_DEFAULT_ENV" in os.environ:
        check_conda_update()
    else:
        check_pypi_update()


def check_pyside_version():
    try:
        import PySide6
    except ImportError:
        input("\033[1;31mPySide6 is not installed but highly recommended.\n\n"
              "Please install it using 'pip install PySide6'.\n\n"
              "Press any key to continue...\033[0m")


def check_conda_update():
    ab_url = "https://api.anaconda.org/package/lca/activity-browser"
    ab_response = requests.get(ab_url)
    ab_current = metadata.version("activity_browser")
    print(f"Activity Browser version: {ab_current}")

    if ab_response.status_code != 200:
        print("Could not fetch latest Activity Browser version")

    elif ab_current != "0.0.0" and ab_current != ab_response.json()['latest_version']:
        input("\033[1;31mThere is an update available for the Activity Browser. Please update it using the following command: \n "
              "conda update -c lca activity-browser\n\n"
              "Press any key to continue without updating...\033[0m")


def check_pypi_update():
    ab_url = "https://pypi.org/pypi/activity-browser/json"
    ab_response = requests.get(ab_url)
    ab_current = metadata.version("activity_browser")
    print(f"Activity Browser version: {ab_current}")

    if ab_response.status_code != 200:
        print("Could not fetch latest Activity Browser version")

    elif ab_current != "0.0.0" and ab_current != ab_response.json()['info']['version']:
        input("\033[1;31mThere is an update available for the Activity Browser. Please update it using the following command: \n "
              "pip install --upgrade activity-browser\n\n"
              "Press any key to continue without updating...\033[0m")


if "--no-launcher" in sys.argv:
    run_activity_browser_no_launcher()
elif sys.version_info[1] == 10:
    log.info("Running Activity Browser without launcher for Python 3.10")
    run_activity_browser_no_launcher()
else:
    run_activity_browser()
