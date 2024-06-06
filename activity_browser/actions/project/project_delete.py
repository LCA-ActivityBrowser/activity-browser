from PySide2 import QtWidgets

from activity_browser import application, ab_settings
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets import ProjectDeletionDialog


class ProjectDelete(ABAction):
    """
    ABAction to delete the currently active project. Return if it's the startup project.
    """
    icon = qicons.delete
    text = "Delete"
    tool_tip = "Delete the project"

    @staticmethod
    @exception_dialogs
    def run():
        # get the current project
        project_to_delete = bd.projects.current

        # if it's the startup project: reject deletion and inform user
        if project_to_delete == ab_settings.startup_project:
            QtWidgets.QMessageBox.information(
                application.main_window, "Not possible",
                "Can't delete the startup project. Please select another startup project in the settings first."
            )
            return

        # open a delete dialog for the user to confirm, return if user rejects
        delete_dialog = ProjectDeletionDialog.construct_project_deletion_dialog(application.main_window,
                                                                                bd.projects.current)
        if delete_dialog.exec_() != ProjectDeletionDialog.Accepted: return

        # try to delete the project, delete directory if user specified so
        bd.projects.set_current(ab_settings.startup_project)
        bd.projects.delete_project(project_to_delete, delete_dialog.deletion_warning_checked())

        # inform the user of successful deletion
        QtWidgets.QMessageBox.information(
            application.main_window,
            "Project deleted",
            "Project successfully deleted"
        )
