import os
import json
import tarfile
from logging import getLogger

from qtpy import QtWidgets, QtCore
import platformdirs

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.threading import ABThread

log = getLogger(__name__)


class ProjectCreateTemplate(ABAction):
    """
    ABAction to export the current project. Prompts the user to return a save-file location. And then start a thread to
    package the project and save it there. Saving code copied from bw2data.backup.
    """
    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)
    text = "Create template for project"
    tool_tip = "Export project to file"

    @staticmethod
    @exception_dialogs
    def run(project_name: str = None, parent=None):
        """Export the current project to a folder chosen by the user."""
        if project_name is None:
            project_name = bd.projects.current

        # get target path from the user
        template_name, ok = QtWidgets.QInputDialog.getText(
            parent if parent else application.main_window,
            "Create template from project",
            f"Creating new template from project ({project_name}):"
            + " " * 10,
        )

        if not ok or not template_name:
            return

        template_file = template_name.strip() + ".tar.gz"
        base_dir = platformdirs.user_data_dir(appname="ActivityBrowser", appauthor="ActivityBrowser")
        template_path = os.path.join(base_dir, "templates", template_file)

        os.makedirs(os.path.join(base_dir, "templates"), exist_ok=True)

        if os.path.exists(template_path):
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A template with this name already exists.",
            )
            return

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=parent if parent else application.main_window,
            labelText="Creating template",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Creating template")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        thread = TemplateThread(application)
        setattr(thread, "save_path", template_path)
        setattr(thread, "project_name", project_name)
        thread.finished.connect(lambda: progress.deleteLater())
        thread.start()


class TemplateThread(ABThread):
    save_path: str
    project_name: str

    def run_safely(self):
        project_dir = str(os.path.join(bd.projects._base_data_dir, bd.utils.safe_filename(self.project_name)))

        with open(os.path.join(project_dir, ".project-name.json"), "w") as f:
            json.dump({"name": self.project_name}, f)

        log.info("Creating project template - this could take a few minutes...")
        with tarfile.open(self.save_path, "w:gz") as tar:
            tar.add(project_dir, arcname=bd.utils.safe_filename(self.project_name))

        log.info(f"Created template from `{self.project_name}`.")
