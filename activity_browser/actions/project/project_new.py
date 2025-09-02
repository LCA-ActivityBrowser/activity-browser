from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ProjectNew(ABAction):
    """
    Prompts the user to create a new project by entering a name. If the name is valid and not already in use,
    a new project is created and set as the current project.

    Steps:
    - Open a dialog to get the new project name from the user.
    - Return if the user cancels or provides an empty name.
    - Check if the name already exists and show an error message if it does.
    - Create a new project with the given name and set it as the current project.

    Raises:
        None
    """

    icon = qicons.add
    text = "New project"
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
