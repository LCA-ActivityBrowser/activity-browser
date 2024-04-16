from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.brightway.bw2data import projects
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons


class ProjectDuplicate(ABAction):
    """
    ABAction to duplicate a project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Else, instructs the ProjectController to duplicate the current
    project to the new name.
    """
    icon = qicons.copy
    title = "Duplicate"
    tool_tip = "Duplicate the project"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Duplicate current project",
            f"Duplicate current project ({projects.current}) to new name:" + " " * 10
        )

        if not ok or not name: return

        if name in projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists."
            )
            return

        projects.copy_project(name)