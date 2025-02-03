from qtpy import QtWidgets, QtGui, QtCore

from bw2data.project import projects

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread


class ProjectMigrate25(ABAction):
    """
    ABAction to duplicate a project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Else, instructs the ProjectController to duplicate the current
    project to the new name.
    """

    icon = qicons.copy
    text = "Migrate project"
    tool_tip = "Migrate the project to bw25"

    @staticmethod
    @exception_dialogs
    def run(name: str = None):
        if name is None:
            name = projects.current

        dialog = MigrateDialog(name, application.main_window)
        dialog.exec_()

        if dialog.result() == dialog.DialogCode.Rejected:
            return

        if name != projects.current:
            projects.set_current(name, update=False)

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=application.main_window,
            labelText="Migrating project, this may take a while...",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Migrating project to Brightway25")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        thread = MigrateThread(application)
        thread.finished.connect(lambda: progress.deleteLater())
        thread.start()


class MigrateDialog(QtWidgets.QDialog):
    def __init__(self, project_name: str, parent=None):
        from .project_export import ProjectExport

        super().__init__(parent)
        self.setWindowTitle("Migrate project")
        label = QtWidgets.QLabel(f"Migrate project ({project_name}) from legacy to Brightway25. This cannot be undone.")

        cancel = QtWidgets.QPushButton("Cancel")
        migrate = QtWidgets.QPushButton("Migrate")
        backup = ProjectExport.get_QButton(project_name)
        backup.setText("Back-up project")
        backup.setIcon(QtGui.QIcon())

        cancel.clicked.connect(self.reject)
        migrate.clicked.connect(self.accept)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(backup)
        button_layout.addStretch()
        button_layout.addWidget(cancel)
        button_layout.addWidget(migrate)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(button_layout)

        self.setLayout(layout)


class MigrateThread(ABThread):
    def run_safely(self):
        projects.migrate_project_25()
        projects.set_current(projects.current)

