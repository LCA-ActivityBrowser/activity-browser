import os

from bw2data.project import projects, ProjectDataset
from bw2data.backends.peewee import SubstitutableDatabase
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import log, signals, application


class ProjectController(QObject):

    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    projects_changed: SignalInstance = Signal()
    project_switched: SignalInstance = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    # mimicking the iterable behaviour of bw2data.projects
    def __getitem__(self, item) -> dict:
        return projects[item]

    def __iter__(self) -> str:
        for project in projects:
            yield project

    # mirroring all public properties of bw2data.projects
    @property
    def current(self) -> str:
        return projects.current

    @property
    def dir(self) -> str:
        return projects.dir

    @property
    def logs_dir(self) -> str:
        return projects.logs_dir

    @property
    def output_dir(self) -> str:
        return projects.logs_dir

    @property
    def read_only(self) -> bool:
        return projects.read_only

    # mirroring all public methods of bw2data.projects
    def copy_project(self, new_name, switch=True) -> None:
        projects.copy_project(new_name, switch)

        signals.projects_changed.emit()
        self.projects_changed.emit()

        if not switch: return

        signals.project_selected.emit()
        signals.databases_changed.emit()

        self.project_switched.emit()

    def create_project(self, name=None, **kwargs) -> None:
        projects.create_project(name, **kwargs)

        signals.projects_changed.emit()
        signals.project_selected.emit()

        self.projects_changed.emit()
        self.project_switched.emit()

    def delete_project(self, name=None, delete_dir=False) -> str:
        """
        Delete the currently active project. Reject if it's the last one.
        """
        current_project = projects.delete_project(name, delete_dir)

        signals.projects_changed.emit()  # legacy
        self.projects_changed.emit()

        return current_project

    def purge_deleted_directories(self) -> int:
        number_of_directories = projects.purge_deleted_directories()

        return number_of_directories

    def report(self):
        report = projects.report()
        return report

    def request_directory(self, name: str) -> str:
        path = projects.request_directory(name)
        return path

    def set_current(self, name, writable=True, update=True) -> None:
        log.info(f"Loading brightway2 project: {name}")
        projects.set_current(name, writable, update)

        signals.project_selected.emit()
        signals.databases_changed.emit()

        self.project_switched.emit()

    # backwards compatibility
    def change_project(self, name: str = "default", reload: bool = False) -> None:
        self.set_current(name)

    def new_project(self, name: str) -> None:
        self.create_project(name)

    # brightway extensions
    @property
    def base_dir(self) -> str:
        return projects._base_data_dir

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
