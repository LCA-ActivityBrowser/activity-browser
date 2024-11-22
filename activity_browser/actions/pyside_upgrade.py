import qtpy
import os
import sys
import subprocess

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class PysideUpgrade(ABAction):
    """
    ABAction to install all the default data: biosphere, IC's etcetera.
    """

    icon = qicons.forward
    text = "Upgrade installation to PySide6"

    @classmethod
    @exception_dialogs
    def run(cls):
        assert not qtpy.PYSIDE6, "Already running PySide6"
        assert cls.in_conda(), "Not inside a Conda environment"

        cls.pypi_install()
        cls.set_conda_env_var()
        cls.restart()


    @staticmethod
    def in_conda() -> bool:
        return bool(os.environ.get("CONDA_DEFAULT_ENV", False))

    @staticmethod
    def pypi_install():
        process = subprocess.run(["pip", "install", "pyside6"])
        assert process.returncode == 0, "Failed to install PySide6"

    @staticmethod
    def set_conda_env_var():
        subprocess.run(["conda", "env", "config", "vars", "set", "QT_API=pyside6"])
        os.environ["QT_API"] = "pyside6"

    @staticmethod
    def restart():
        subprocess.Popen(["python", "-c", "import activity_browser; activity_browser.run_activity_browser()"])
        sys.exit()

