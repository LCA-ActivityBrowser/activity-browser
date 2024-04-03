import brightway2 as bw
from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from activity_browser import application, project_controller
from activity_browser.actions.base import ABAction, dialog_on_error
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

    @dialog_on_error
    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Duplicate current project",
            f"Duplicate current project ({bw.projects.current}) to new name:" + " " * 10
        )

        if not ok or not name: return

        if name in bw.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists."
            )
            return

        project_controller.copy_project(name)
