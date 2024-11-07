import codecs
import json
import tarfile
from logging import getLogger

from qtpy import QtWidgets, QtCore
from bw2io import backup

from activity_browser import application
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons
from activity_browser.ui.threading import ABThread

log = getLogger(__name__)


class ProjectImport(ABAction):
    """
    ABAction to import a new project. Prompts the user to select a file. Imports the project name from the file as a
    suggestion. Prompts user to either accept the name or change it. If the name already exists, try again. Else,
    perform the import in a separate thread and show a progress dialog until it is finished. Finally, move to the newly
    imported project.
    """
    icon = qicons.import_db
    text = "&Import a project..."
    tool_tip = "Import project from a file"

    @classmethod
    @exception_dialogs
    def run(cls):
        """Import a project into AB based on file chosen by user."""

        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=application.main_window,
            caption='Choose project file to import',
            filter='Tar archive (*.tar.gz);; All files (*.*)'
        )
        if not path: return

        # create a name suggestion based on the file name
        suggestion = cls.get_project_name(path)

        # get a new project name from the user:
        while True:
            project_name, _ = QtWidgets.QInputDialog.getText(
                application.main_window,
                'Choose project name',
                'Choose a name for your project',
                text=suggestion
            )

            if not project_name: return

            if project_name in bd.projects:
                # this name already exists, inform user and ask again.
                QtWidgets.QMessageBox.information(
                    application.main_window,
                    "Not possible.",
                    "A project with this name already exists."
                )
            else: break

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=application.main_window,
            labelText="Importing project",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Importing project")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        # setup the import
        thread = ImportThread(application)
        setattr(thread, "path", path)
        setattr(thread, "project_name", project_name)

        thread.finished.connect(lambda: progress.deleteLater())
        thread.finished.connect(lambda: bd.projects.set_current(project_name))

        # start the import
        thread.start()

    @staticmethod
    def get_project_name(fp):
        reader = codecs.getreader("utf-8")
        # See https://stackoverflow.com/questions/68997850/python-readlines-with-tar-file-gives-streamerror-seeking-backwards-is-not-al/68998071#68998071
        with tarfile.open(fp, "r:gz") as tar:
            for member in tar:
                if member.name[-17:] == "project-name.json":
                    return json.load(reader(tar.extractfile(member)))["name"]
            raise ValueError("Couldn't find project name file in archive")


class ImportThread(ABThread):

    def run_safely(self):
        log.debug('Starting project import:'
                  f'\nPATH: {self.path}'
                  f'\nNAME: {self.project_name}')
        backup.restore_project_directory(fp=self.path, project_name=self.project_name)
        log.info(f"Project `{self.project_name}` imported.")

