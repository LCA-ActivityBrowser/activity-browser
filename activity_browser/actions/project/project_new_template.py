from qtpy import QtWidgets, QtCore
from logging import getLogger

import bw2data as bd
from bw2io import backup

from activity_browser import application, utils
from activity_browser.actions.base import ABAction, exception_dialogs

from activity_browser.ui.threading import ABThread
from activity_browser.ui.icons import qicons

log = getLogger(__name__)


class ProjectNewFromTemplate(ABAction):
    """
    ABAction to create a new project from a remote template.
    """

    icon = qicons.add
    text = "New project from remote"
    tool_tip = "Make a new project from remote template"

    @staticmethod
    @exception_dialogs
    def run(template_key: str):

        if template_key not in utils.get_templates():
            raise ValueError(f"Template key '{template_key}' not found.")

        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create project from template",
            "Name of new project:" + " " * 25,
        )

        if not ok or not name:
            return

        if name in bd.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists.",
            )
            return

        # setup dialog
        progress = QtWidgets.QProgressDialog(
            parent=application.main_window,
            labelText="Creating project from template",
            maximum=0
        )
        progress.setCancelButton(None)
        progress.setWindowTitle("Creating project from template")
        progress.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        progress.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        progress.findChild(QtWidgets.QProgressBar).setTextVisible(False)
        progress.resize(400, 100)
        progress.show()

        # setup the import
        thread = ImportThread(application)
        setattr(thread, "path", utils.get_templates()[template_key])
        setattr(thread, "project_name", name)

        thread.finished.connect(lambda: progress.deleteLater())
        thread.finished.connect(lambda: bd.projects.set_current(name))

        # start the import
        thread.start()


class ImportThread(ABThread):
    path: str
    project_name: str

    def run_safely(self):
        log.debug('Creating project from template:'
                  f'\nPATH: {self.path}'
                  f'\nNAME: {self.project_name}')
        backup.restore_project_directory(fp=self.path, project_name=self.project_name)
        log.info(f"Project `{self.project_name}` created.")


