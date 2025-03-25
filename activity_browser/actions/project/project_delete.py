from qtpy import QtWidgets

from activity_browser import settings, application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ProjectDelete(ABAction):
    """
    ABAction to delete the currently active project. Return if it's the startup project.
    """

    icon = qicons.delete
    text = "Delete"
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
