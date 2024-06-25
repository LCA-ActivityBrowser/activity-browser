import os
import json
import tarfile

from PySide2 import QtWidgets, QtCore

from activity_browser import application, log
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.threading import ABThread


class ProjectExport(ABAction):
    """
    ABAction to export the current project. Prompts the user to return a save-file location. And then start a thread to
    package the project and save it there. Saving code copied from bw2data.backup.
    """
    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)
    text = "&Export this project..."
    tool_tip = "Export project to file"

    @staticmethod
    @exception_dialogs
    def run():
        """Export the current project to a folder chosen by the user."""
        # get target path from the user
        save_path, save_type = QtWidgets.QFileDialog.getSaveFileName(
            parent=application.main_window,
            caption="Choose where",
            dir=os.path.expanduser(f"~/{bd.projects.current}.tar.gz"),
            filter="Tar-file (*.tar.gz)"
        )

        if not save_path: return

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=application.main_window,
            labelText="Exporting project",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Exporting project")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        thread = ExportThread(application)
        setattr(thread, "save_path", save_path)
        thread.finished.connect(lambda: progress.deleteLater())
        thread.start()


class ExportThread(ABThread):

    def run_safely(self):
        project_name = bd.projects.current
        project_dir = os.path.join(bd.projects._base_data_dir, bd.utils.safe_filename(project_name))

        with open(os.path.join(project_dir, ".project-name.json"), "w") as f:
            json.dump({"name": project_name}, f)

        log.info("Creating project backup archive - this could take a few minutes...")
        with tarfile.open(self.save_path, "w:gz") as tar:
            tar.add(project_dir, arcname=bd.utils.safe_filename(project_name))

        log.info(f"Project `{project_name}` exported.")
