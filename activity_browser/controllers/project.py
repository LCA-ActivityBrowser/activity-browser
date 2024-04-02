import os

import brightway2 as bw
from bw2data.project import projects, ProjectDataset
from bw2data.backends.peewee import SubstitutableDatabase
from PySide2.QtCore import QObject, Signal

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


class NewProjectController(QObject):

    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    projects_changed = Signal()
    project_switched = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    # mimicking the iterable behaviour of bw2data.projects
    def __getitem__(self, item):
        return projects[item]

    def __iter__(self):
        for project in projects:
            yield project

    # mirroring all public properties and methods of bw2data.projects
    @property
    def current(self):
        return projects.current

    @property
    def dir(self):
        return projects.dir

    @property
    def logs_dir(self):
        return projects.logs_dir

    @property
    def output_dir(self):
        return projects.logs_dir

    @property
    def read_only(self):
        return projects.read_only

    def copy_project(self, new_name, switch=True):
        projects.copy_project(new_name, switch)

        signals.projects_changed.emit()
        self.projects_changed.emit()

    def create_project(self, name=None, **kwargs):
        projects.create_project(name, **kwargs)

        signals.projects_changed.emit()
        self.projects_changed.emit()

    def delete_project(self, name=None, delete_dir=False) -> str:
        """
        Delete the currently active project. Reject if it's the last one.
        """
        current_project = projects.delete_project(name, delete_dir)

        signals.projects_changed.emit()
        self.projects_changed.emit()

        return current_project

    def purge_deleted_directories(self):
        number_of_directories = projects.purge_deleted_directories()

        return number_of_directories

    def report(self):
        report = projects.report()
        return report

    def request_directory(self, name: str) -> str:
        path = projects.request_directory(name)
        return path

    def set_current(self, name, writable=True, update=True):
        log.info(f"Loading brightway2 project: {name}")
        projects.set_current(name, writable, update)

        signals.project_selected.emit()
        signals.databases_changed.emit()

        self.project_switched.emit()

    # backwards compatibility
    def change_project(self, name: str = "default", reload: bool = False) -> None:
        self.set_current(name)

    def new_project(self, name: str):
        self.create_project(name)

    # brightway extensions
    def switch_dir(self, path: str) -> None:
        log.info(f"Switching project directory to: {path}")

        projects._base_data_dir = path
        projects._base_logs_dir = os.path.join(path, "logs")
        if not os.path.isdir(projects._base_logs_dir):
            os.mkdir(projects._base_logs_dir)

        projects.db = SubstitutableDatabase(
            os.path.join(projects._base_data_dir, "projects.db"),
            [ProjectDataset]
        )

        signals.project_selected.emit()
        signals.databases_changed.emit()

        self.project_switched.emit()


project_controller = ProjectController(application)
