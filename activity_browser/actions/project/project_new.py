from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ProjectNew(ABAction):
    """
    ABAction to create a new project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Otherwise, instructs the ProjectController to create a new
    project with the given name, and switch to it.
    """

    icon = qicons.add
    text = "New"
    tool_tip = "Make a new project"

    @staticmethod
    @exception_dialogs
    def run():
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new project",
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

        bd.projects.create_project(name)
        bd.projects.set_current(name)
