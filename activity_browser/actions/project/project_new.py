from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.brightway.bw2data import projects
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ProjectNew(ABAction):
    """
    ABAction to create a new project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Otherwise, instructs the ProjectController to create a new
    project with the given name, and switch to it.
    """
    icon = qicons.add
    title = "New"
    tool_tip = "Make a new project"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new project",
            "Name of new project:" + " " * 25
        )

        if not ok or not name: return

        if name in projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists."
            )
            return

        projects.create_project(name)
        projects.set_current(name)
