from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod.bw2io import remote
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


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

        remote.install_project(project_key, name)
        bd.projects.set_current(name)
