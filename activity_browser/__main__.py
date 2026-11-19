# Divert the program flow in worker sub-process as soon as possible,
# before importing heavy-weight modules.
if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

import sys
import os
import traceback
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

        self._module_thread = None
        self.load_modules()

    def load_modules(self):
        self._module_thread = ModuleThread(self)
        # QThread.finished fires on success and failure; check thread.error before continuing.
        self._module_thread.finished.connect(self._on_modules_finished)
        self._module_thread.status.connect(self.text_label.setText)
        self._module_thread.start()

    def _on_modules_finished(self):
        error = getattr(self._module_thread, "error", None)
        if error is not None:
            self._on_load_failed(error)
            return
        self.load_finished()

    def load_finished(self):
        # Most of startup wall time is here (app package + apply_settings), not in ModuleThread.
        try:
            self.text_label.setText("Building main window")
            from activity_browser import app

            load_plugins()

            app.main_window.show()
            self.deleteLater()
        except Exception as e:
            self._on_load_failed(e)

    def _on_load_failed(self, exc: BaseException):
        show_startup_failure(exc, parent=self)
        qapp = QtWidgets.QApplication.instance()
        if qapp is not None:
            qapp.quit()


class ModuleThread(QtCore.QThread):
    status: QtCore.SignalInstance = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.error: BaseException | None = None

    def run(self):
        self.error = None
        try:
            self._load_modules()
        except Exception as e:
            logger.exception("Failed to load startup modules")
            self.error = e

    def _load_modules(self):
        self.status.emit("Loading Numpy")
        logger.debug("ABLoader: Importing numpy and pandas")
        import numpy, pandas
        from activity_browser.bwutils.pandas_semantics import apply_pandas_3_semantics
        apply_pandas_3_semantics()
        self.status.emit("Loading Brightway25")
        logger.debug("ABLoader: Importing brightway modules")
        import bw2data, bw2calc, bw2analyzer, bw2io, bw_functional, bw_processing, matrix_utils


STARTUP_FAILURE_TITLE = "Activity Browser failed to start"


def show_startup_failure(exc: BaseException, parent=None) -> None:
    """Show a single actionable dialog when startup cannot continue.

    Prints the traceback to stderr (copyable from the console) and exposes the
    same text via Show Details plus a Copy details button — QMessageBox summary
    labels are not reliably selectable on Windows.
    """
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    summary = f"{type(exc).__name__}: {exc}"
    details = f"{summary}\n\n{tb}".rstrip() + "\n"

    logger.opt(exception=exc).error(STARTUP_FAILURE_TITLE)
    print(details, file=sys.stderr, flush=True)

    text = (
        f"{summary}\n\n"
        "Startup could not continue. Check that your Python environment "
        "matches the install instructions, then reinstall Activity Browser "
        "dependencies if needed.\n\n"
        "Use Show Details or Copy details for the full traceback "
        "(also printed to the console)."
    )

    # Nested so tests can swap QtWidgets.QMessageBox and still inherit the patch.
    class StartupFailureBox(QtWidgets.QMessageBox):
        def __init__(self, details_text: str, parent=None):
            super().__init__(parent)
            self._details = details_text
            self._copy_btn = self.addButton(
                "Copy details", QtWidgets.QMessageBox.ActionRole
            )
            self.addButton(QtWidgets.QMessageBox.Ok)
            self._copy_btn.clicked.connect(self._copy_details)

        def _copy_details(self) -> None:
            qapp = QtWidgets.QApplication.instance()
            if qapp is not None:
                qapp.clipboard().setText(self._details)

        def done(self, result: int) -> None:
            # Keep the dialog open when Copy details is clicked.
            if self.clickedButton() is self._copy_btn:
                return
            super().done(result)

    box = StartupFailureBox(details, parent)
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setWindowTitle(STARTUP_FAILURE_TITLE)
    box.setText(text)
    box.setDetailedText(details)
    box.exec_()


def run_activity_browser():
    from activity_browser.ui.core.application import ABApplication
    app = ABApplication()

    pre_flight_checks()
    loader = ABLoader()
    loader.show()

    app.set_icon()  # setting this here seems to fix the icon not showing sometimes
    sys.exit(app.exec_())

def run_activity_browser_no_launcher():
    pre_flight_checks()

    modules = ModuleThread()
    modules.run()
    if modules.error is not None:
        show_startup_failure(modules.error)
        sys.exit(1)

    try:
        from .ui.widgets import ABCentralPagesWidget
        from .app import panes, pages, application, metadata

        load_plugins()

        application.main_window.show()

        application.set_icon()  # setting this here seems to fix the icon not showing sometimes
        sys.exit(application.exec_())
    except Exception as e:
        logger.exception("Failed to build the main window")
        show_startup_failure(e)
        sys.exit(1)


def pre_flight_checks():
    """Always print the stamped version (smoke needs it under ``--no-checks``).

    Network update prompts stay on the legacy path until the updates PR lands.
    """
    try:
        current = metadata.version("activity_browser")
    except metadata.PackageNotFoundError:
        current = "0.0.0"
    # Frozen/stand-alone builds stamp the public AB version; display adds the channel suffix.
    display = f"{current}-stand-alone" if getattr(sys, "frozen", False) else current
    version_line = f"Activity Browser version: {display}"
    print(version_line, flush=True)
    logger.info(version_line)

    if "--no-checks" in sys.argv:
        return

    if "CONDA_DEFAULT_ENV" in os.environ:
        check_conda_update(current)
    else:
        check_pypi_update(current)


def check_conda_update(ab_current: str):
    ab_url = "https://api.anaconda.org/package/lca/activity-browser"
    try:
        ab_response = requests.get(ab_url)
    except:
        print("Could not fetch latest Activity Browser version")
        return

    if ab_response.status_code != 200:
        print("Could not fetch latest Activity Browser version")

    elif ab_current != "0.0.0" and ab_current != ab_response.json()['latest_version']:
        input("\033[1;31mThere is an update available for the Activity Browser. Please update it using the following command: \n "
              "conda update -c conda-forge -c cmutel -c lca activity-browser\n\n"
              "Complete installation instructions can be found here:\n\n"
              "https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html#installing-from-anaconda\n\n"
              "Press any key to continue without updating...\033[0m")


def check_pypi_update(ab_current: str):
    ab_url = "https://pypi.org/pypi/activity-browser/json"
    try:
        ab_response = requests.get(ab_url)
    except:
        print("Could not fetch latest Activity Browser version")
        return

    if ab_response.status_code != 200:
        print("Could not fetch latest Activity Browser version")

    elif ab_current != "0.0.0" and ab_current != ab_response.json()['info']['version']:
        input("\033[1;31mThere is an update available for the Activity Browser. Please update it using the following command: \n "
              "pip install --upgrade activity-browser\n\n"
              "Complete installation instructions can be found here:\n\n"
              "https://lca-activitybrowser.github.io/activity-browser/getting-started/installation.html#installing-from-pypi\n\n"
              "Press any key to continue without updating...\033[0m")

def load_plugins():
    from activity_browser.bwutils.settings import Settings
    settings = Settings()
    plugins = settings["plugins"].get("enabled_plugins", [])
    for plugin in plugins:
        try:
            __import__(plugin)
            logger.info(f"Successfully loaded plugin: {plugin}")
        except ImportError:
            logger.warning(f"Could not load plugin: {plugin}")


if __name__ == "__main__":
    if "--no-launcher" in sys.argv:
        run_activity_browser_no_launcher()
    else:
        run_activity_browser()
