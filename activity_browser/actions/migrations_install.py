from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons, threading
from activity_browser.mod.bw2io.migrations import ab_create_core_migrations


class MigrationsInstall(ABAction):
    """
    ABAction to install the default migrations from bw2io
    """

    icon = icons.qicons.import_db
    text = "Install default migrations"

    @staticmethod
    @exception_dialogs
    def run():
        def update_dialog_slot(progress: int, label: str):
            dialog.setValue(progress)
            dialog.setLabelText(label)


        dialog = QtWidgets.QProgressDialog(application.main_window)
        dialog.setWindowTitle("Installing migrations")
        dialog.setMaximum(100)
        dialog.setCancelButton(None)

        thread = MigrationsInstallThread(application)

        thread.status.connect(update_dialog_slot)

        thread.start()
        dialog.exec_()


class MigrationsInstallThread(threading.ABThread):
    def run_safely(self):
        ab_create_core_migrations()
