# Divert the program flow in worker sub-process as soon as possible,
# before importing heavy-weight modules.
if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

import sys
import os
from importlib import metadata

import requests

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

# this will enable the AB icon to show in the taskbar under Windows 11 (instead of the default python icon)
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("activity.browser.1")

from loguru import logger
import platformdirs
from .static.icons import main




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
        self.setWindowFlags(Qt.FramelessWindowHint)
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
        self.load_finished()

    def load_finished(self):
        from activity_browser import app
        app.main_window.show()
        self.deleteLater()


class ModuleThread(QtCore.QThread):
    status: QtCore.SignalInstance = QtCore.Signal(str)

    def run(self):
        self.status.emit("Loading Numpy")
        logger.debug("ABLoader: Importing numpy")
        import numpy, pandas
        self.status.emit("Loading Brightway25")
        logger.debug("ABLoader: Importing brightway modules")
        import bw2data, bw2calc, bw2analyzer, bw2io, bw_functional, bw_processing, matrix_utils


def setup_logging():
    """Configure loguru sinks for console and file logging."""
    logger.level("SYNC", no=9, color="<cyan>")
    logger.level("TEST", no=19, color="<cyan>")


    logger.remove()
    logger.add(sys.stderr, level=6, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

    log_dir = platformdirs.user_log_dir(appname="ActivityBrowser", appauthor="pylca")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "activity_browser.log")
    logger.add(log_file, level="DEBUG", rotation="5 MB", retention=5)


def run_activity_browser():
    from activity_browser.ui.core.application import ABApplication
    app = ABApplication()

    pre_flight_checks()
    setup_logging()
    loader = ABLoader()
    loader.show()

    app.set_icon()  # setting this here seems to fix the icon not showing sometimes
    sys.exit(app.exec_())


def run_activity_browser_no_launcher():
    pre_flight_checks()
    setup_logging()

    modules = ModuleThread()
    modules.run()

    from .ui.widgets import CentralTabWidget
    from .app import panes, pages, application, metadata

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
              "Please install it using 'pip install PySide6==6.9.3'.\n\n"
              "Press any key to continue...\033[0m")


def check_conda_update():
    ab_url = "https://api.anaconda.org/package/lca/activity-browser"
    try:
        ab_response = requests.get(ab_url)
    except:
        print("Could not fetch latest Activity Browser version")
        return
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
    try:
        ab_response = requests.get(ab_url)
    except:
        print("Could not fetch latest Activity Browser version")
        return
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
    logger.info("Running Activity Browser without launcher for Python 3.10")
    run_activity_browser_no_launcher()
else:
    run_activity_browser()
