from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons

from .project_switch import ProjectSwitch


class ProjectDuplicate(ABAction):
    """
    Duplicate the current project to a new name.

    This method prompts the user to input a new name for duplicating the current project.
    It performs validation to ensure the new name is not empty and does not already exist.
    If the provided name is valid, the current project is duplicated to the new name, and
    the application switches to the newly created project.

    Args:
        name (str, optional): The name of the current project to duplicate. Defaults to the
                              currently active project.

    Steps:
    - If no name is provided, use the current project name.
    - Prompt the user for a new project name.
    - Return if the user cancels or provides an empty name.
    - Check if the new name already exists and show an error message if it does.
    - If the provided name is not the current project, set it as the current project.
    - Duplicate the project to the new name without switching to it.
    - Switch to the newly created project using the `ProjectSwitch` action.
    """

    icon = qicons.copy
    text = "Duplicate this project"
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
