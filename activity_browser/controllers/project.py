# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser import log, signals, ab_settings, application
from activity_browser.bwutils import commontasks as bc
from activity_browser.ui.widgets import ProjectDeletionDialog

class ProjectController(QObject):
    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)
        signals.change_project.connect(self.change_project)
        signals.new_project.connect(self.new_project)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)

    @Slot(str, name="switchBwDirPath")
    def switch_brightway2_dir_path(self, dirpath: str) -> None:
        if bc.switch_brightway2_dir(dirpath):
            self.change_project(ab_settings.startup_project, reload=True)
            signals.databases_changed.emit()

    def load_settings(self) -> None:
        if ab_settings.settings:
            log.info("Loading user settings:")
            self.switch_brightway2_dir_path(dirpath=ab_settings.current_bw_dir)
            self.change_project(ab_settings.startup_project)
        log.info('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        log.info('Brightway2 active project: {}'.format(bw.projects.current))

    @staticmethod
    @Slot(str, name="changeProject")
    def change_project(name: str = "default", reload: bool = False) -> None:
        """Change the project, this clears all tabs and metadata related to
        the current project.
        """
        # check whether the project does exist, otherwise return
        if name not in bw.projects: 
            log.info(f"Project does not exist: {name}")
            return
        
        if name != bw.projects.current or reload:
            bw.projects.set_current(name)
        signals.project_selected.emit()
        log.info("Loaded project:", name)

    @Slot(name="createProject")
    def new_project(self, name=None):
        if name is None:
            name, ok = QtWidgets.QInputDialog.getText(
                application.main_window,
                "Create new project",
                "Name of new project:" + " " * 25
            )
            if not ok or not name:
                return

        if name and name not in bw.projects:
            bw.projects.set_current(name)
            self.change_project(name, reload=True)
            signals.projects_changed.emit()
        elif name in bw.projects:
            QtWidgets.QMessageBox.information(
                application.main_window, "Not possible.",
                "A project with this name already exists."
            )

    @Slot(name="copyProject")
    def copy_project(self):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Copy current project",
            "Copy current project ({}) to new name:".format(bw.projects.current) + " " * 10
        )
        if ok and name:
            if name not in bw.projects:
                bw.projects.copy_project(name, switch=True)
                self.change_project(name)
                signals.projects_changed.emit()
            else:
                QtWidgets.QMessageBox.information(
                    application.main_window, "Not possible.",
                    "A project with this name already exists."
                )

    @Slot(name="deleteProject")
    def delete_project(self):
        """
        Delete the currently active project. Reject if it's the last one.
        """
        project_to_delete: str = bw.projects.current

        # if it's the startup project: reject deletion and inform user
        if project_to_delete == ab_settings.startup_project:
            QtWidgets.QMessageBox.information(
                application.main_window, "Not possible", "Can't delete the startup project. Please select another startup project in the settings first."
            )
            return

        # open a delete dialog for the user to confirm, return if user rejects
        delete_dialog = ProjectDeletionDialog.construct_project_deletion_dialog(application.main_window, bw.projects.current)
        if delete_dialog.exec_() != ProjectDeletionDialog.Accepted: return

        # change from the project to be deleted, to the startup project
        self.change_project(ab_settings.startup_project, reload=True)

        # try to delete the project, delete directory if user specified so
        try:
            bw.projects.delete_project(
                project_to_delete, 
                delete_dir=delete_dialog.deletion_warning_checked()
                )
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

        # emit that the project list has changed because of the deletion,
        # regardless of a possible exception (which may have deleted the project anyways) 
        signals.projects_changed.emit()

project_controller = ProjectController(application)