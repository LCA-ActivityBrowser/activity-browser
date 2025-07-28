from qtpy import QtWidgets

import bw2data as bd

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.bw2io import remote
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread

from .project_switch import ProjectSwitch


class ProjectNewRemote(ABAction):
    """
    ABAction to create a new project from a remote template.
    """

    icon = qicons.add
    text = "New project from remote"
    tool_tip = "Make a new project from remote template"

    @staticmethod
    @exception_dialogs
    def run(project_key: str):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create project from remote",
            "Name of new project:" + " " * 25,
        )

        if not ok or not name:
            return

        if name in bd.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists.",
            )
            return

        thread = InstallThread(application)
        thread.start(project_key, name)

        dialog = MigrateDialog(application.main_window)
        dialog.show()

        thread.finished.connect(dialog.close)
        thread.finished.connect(lambda: ProjectSwitch.run(name))


class MigrateDialog(QtWidgets.QProgressDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Installing project")
        self.setLabelText("Restoring project from template, this may take a while...")
        self.setRange(0, 0)
        self.setCancelButton(None)


class InstallThread(ABThread):
    def run_safely(self, project_key: str, name: str):
        remote.install_project(project_key, name)

