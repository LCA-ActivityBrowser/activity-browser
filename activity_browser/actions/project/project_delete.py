import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import application, ab_settings, log
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.ui.widgets import ProjectDeletionDialog
from activity_browser.controllers import project_controller


class ProjectDelete(ABAction):
    """
    ABAction to delete the currently active project. Return if it's the startup project.
    """
    icon = qicons.delete
    title = "Delete"
    tool_tip = "Delete the project"

    def onTrigger(self, toggled):
        # get the current project
        project_to_delete = bw.projects.current

        # if it's the startup project: reject deletion and inform user
        if project_to_delete == ab_settings.startup_project:
            QtWidgets.QMessageBox.information(
                application.main_window, "Not possible",
                "Can't delete the startup project. Please select another startup project in the settings first."
            )
            return

        # open a delete dialog for the user to confirm, return if user rejects
        delete_dialog = ProjectDeletionDialog.construct_project_deletion_dialog(application.main_window,
                                                                                bw.projects.current)
        if delete_dialog.exec_() != ProjectDeletionDialog.Accepted: return

        # try to delete the project, delete directory if user specified so
        try:
            project_controller.delete_project(delete_dialog.deletion_warning_checked())
        # if an exception occurs, show warning box en log exception
        except Exception as exception:
            log.error(str(exception))
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "An error occured",
                "An error occured during project deletion. Please check the logs for more information."
            )
            # if all goes well show info box that the project is deleted
        else:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Project deleted",
                "Project succesfully deleted"
            )
