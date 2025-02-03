from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

from .project_switch import ProjectSwitch


class ProjectDuplicate(ABAction):
    """
    ABAction to duplicate a project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Else, instructs the ProjectController to duplicate the current
    project to the new name.
    """

    icon = qicons.copy
    text = "Duplicate"
    tool_tip = "Duplicate the project"

    @staticmethod
    @exception_dialogs
    def run(name: str = None):
        if name is None:
            name = bd.projects.current

        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Duplicate current project",
            f"Duplicate project ({name}) to new name:"
            + " " * 10,
        )

        if not ok or not new_name:
            return

        if new_name in bd.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists.",
            )
            return

        if name != bd.projects.current:
            bd.projects.set_current(name, update=False)
        bd.projects.copy_project(new_name, switch=False)  # don't switch because it will auto-update bw2 projects
        ProjectSwitch.run(new_name)  # switch using the action instead
