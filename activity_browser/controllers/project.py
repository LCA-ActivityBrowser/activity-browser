# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import QObject

from activity_browser import log, signals, ab_settings, application
from activity_browser.bwutils import commontasks as bc



class ProjectController(QObject):
    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

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

    def new_project(self, name: str):
        bw.projects.set_current(name)
        self.change_project(name, reload=True)
        signals.projects_changed.emit()

    def duplicate_project(self, new_name: str):
        bw.projects.copy_project(new_name, switch=True)
        self.change_project(new_name)
        signals.projects_changed.emit()

    def delete_project(self, delete_dir=False):
        """
        Delete the currently active project. Reject if it's the last one.
        """
        project_to_delete = bw.projects.current

        # change from the project to be deleted, to the startup project
        self.change_project(ab_settings.startup_project, reload=True)

        # try to delete the project, delete directory if user specified so
        bw.projects.delete_project(
            project_to_delete,
            delete_dir=delete_dir
            )

        signals.projects_changed.emit()


project_controller = ProjectController(application)