from qtpy import QtWidgets

from activity_browser import settings, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ProjectDelete(ABAction):
    """
    Deletes the specified projects or the currently active project if no project names are provided.

    This method handles the deletion of Brightway2 projects. It ensures that the startup project
    cannot be deleted, prompts the user for confirmation, and optionally deletes the project
    directories from the hard disk.

    Args:
        project_names (list of str, optional): A list of project names to delete. If None, the
                                               currently active project is selected.

    Steps:
    - If no project names are provided, use the currently active project.
    - Return immediately if the project list is empty.
    - Prevent deletion of the startup project and notify the user if attempted.
    - Open a confirmation dialog for the user to approve the deletion.
    - If the user cancels, return without deleting.
    - If the currently active project is being deleted, switch to the startup project.
    - Delete the specified projects, optionally removing their directories from the hard disk.
    - Notify the user of successful deletion.

    Raises:
        None
    """

    icon = qicons.delete
    text = "Delete this project"
    tool_tip = "Delete the project"

    @staticmethod
    @exception_dialogs
    def run(project_names: [str] = None):
        if project_names is None:
            # get the current project
            project_names = [bd.projects.current]

        if len(project_names) == 0:
            return

        # if it's the startup project: reject deletion and inform user
        if settings.ab_settings.startup_project in project_names:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible",
                "Can't delete the startup project. Please select another startup project in the settings first.",
            )
            return

        # open a delete dialog for the user to confirm, return if user rejects
        delete_dialog = ProjectDeletionDialog(project_names, application.main_window)
        if delete_dialog.exec_() != ProjectDeletionDialog.Accepted:
            return

        # try to delete the project, delete directory if user specified so
        if bd.projects.current in project_names:
            bd.projects.set_current(settings.ab_settings.startup_project)

        for project in project_names:
            bd.projects.delete_project(
                project, delete_dialog.deletion_warning_checked()
            )

        # inform the user of successful deletion
        QtWidgets.QMessageBox.information(
            application.main_window, "Project(s) deleted", "Project(s) successfully deleted"
        )


class ProjectDeletionDialog(QtWidgets.QDialog):

    def __init__(self, projects: [str], parent=None):
        super().__init__(parent)

        self.title = "Confirm project deletion"

        if len(projects) == 1:
            self.label = QtWidgets.QLabel(
                f"Final confirmation to remove project: {projects[0]}.\n"
                + "Warning: Non reversible process!"
            )
        else:
            self.label = QtWidgets.QLabel(
                f"Final confirmation to remove {len(projects)} projects.\n"
                + "Warning: Non reversible process!"
            )
        self.check = QtWidgets.QVBoxLayout()
        self.hd_check = QtWidgets.QCheckBox(f"Remove from the hard disk")
        self.hd_check.setChecked(True)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.setWindowTitle(self.title)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.hd_check)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def deletion_warning_checked(self):
        return self.hd_check.isChecked()
