import qtpy
import os
import sys
import subprocess
import time

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import threading, icons

from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance


class PysideUpgrade(ABAction):
    """
    ABAction to install PySide6 through PyPI/pip. Installs PySide6, sets the environment variable for QtPy to use
    PySide6 and then restarts the Activity Browser through a subprocess.
    """

    icon = icons.qicons.forward
    text = "Upgrade installation to PySide6"

    @classmethod
    @exception_dialogs
    def run(cls):

        # slot definition to update the progress dialog with thread updates
        def update_dialog_slot(progress: int, label: str):
            dialog.setValue(progress)
            dialog.setLabelText(label)

        assert not qtpy.PYSIDE6, "Already running PySide6"
        assert cls.in_conda(), "Not inside a Conda environment"

        # setup a progress dialog to show the user we're doing something
        dialog = QtWidgets.QProgressDialog(application.main_window)
        dialog.setWindowTitle("Upgrading GUI back-end")
        dialog.setMaximum(0)
        dialog.setCancelButton(None)

        # messages can get quite long, so enable word-wrapping
        lbl = dialog.findChild(QtWidgets.QLabel)
        lbl.setWordWrap(True)

        # initialize thread and connect signals
        thread = PySideUpgradeThread(application)
        thread.status.connect(update_dialog_slot)
        thread.exit.connect(sys.exit)

        thread.start()
        dialog.exec_()

    @staticmethod
    def in_conda() -> bool:
        """Returns true when the current shell is in a Conda environment."""
        return bool(os.environ.get("CONDA_DEFAULT_ENV", False))


class PySideUpgradeThread(threading.ABThread):
    exit: SignalInstance = Signal()

    def run_safely(self):
        self.pip_installation()
        self.restart()

    def pip_installation(self):
        """
        Install PySide6 from PyPI using a subprocess.Popen call
        """
        self.status.emit(0, "Installing PySide6 through pip")

        # open subprocess that installs PySide6
        process = subprocess.Popen(["pip", "install", "pyside6"], stdout=subprocess.PIPE)

        while process.poll() is None:  # block until the subprocess is finished
            # format stdout
            line = process.stdout.readline().decode().strip()
            if not line:
                continue

            # redirect stdout to both console and progress dialog
            print(line)
            self.status.emit(0, line)

        assert process.returncode == 0, "Failed to install PySide6"

    def restart(self):
        """
        Restarts the Activity Browser through a subprocess. Sleeps 5 seconds to allow the user to register
        the restart.
        """
        self.status.emit(0, "Restarting the Activity Browser")
        subprocess.Popen(["python", "-c", "import activity_browser; activity_browser.run_activity_browser()"])
        time.sleep(5)

        # signal restart through the exit signal as sys.exit needs to be called in the main thread.
        self.exit.emit()


