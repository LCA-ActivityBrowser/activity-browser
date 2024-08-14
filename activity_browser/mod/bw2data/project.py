from pathlib import Path
import os

from bw2data.project import *

try:
    from bw2data.backends.peewee import SubstitutableDatabase
except ModuleNotFoundError:
    # we're running Brightway 25 so import accordingly
    from bw2data.backends import SubstitutableDatabase

from activity_browser.signals import qprojects

from ..patching import patch_superclass, patched


@patch_superclass
class ProjectManager(ProjectManager):
    @property
    def current_changed(self):
        """
        Shorthand for connecting to the method QUpdater. Developers can import projects from bw2data and connect
        directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qprojects.current_changed

    @property
    def list_changed(self):
        """
        Shorthand for connecting to the method QUpdater. Developers can import projects from bw2data and connect
        directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qprojects.list_changed

    def set_current(self, name, writable=True, update=True):
        # execute the patched function for standard functionality
        patched[ProjectManager]["set_current"](self, name, writable, update)

        # emit that the current project has changed through the qUpdater
        qprojects.emitLater("current_changed")

    def create_project(self, name=None, **kwargs):
        # execute the patched function for standard functionality
        patched[ProjectManager]["create_project"](self, name, **kwargs)

        # emit that the project list has changed through the qUpdater
        qprojects.emitLater("list_changed")

    def copy_project(self, new_name, switch=True):
        # execute the patched function for standard functionality
        patched[ProjectManager]["copy_project"](self, new_name, switch)

        # emit that the project list has changed through the qUpdater
        qprojects.emitLater("list_changed")

    def delete_project(self, name=None, delete_dir=False):
        # execute the patched function for standard functionality
        patched[ProjectManager]["delete_project"](self, name, delete_dir)

        # emit that the project list has changed through the qUpdater
        qprojects.emitLater("list_changed")

    # extending functionality
    @property
    def base_dir(self) -> str:
        """
        We keep using the protected property anyway, so why not make it available.
        """
        return projects._base_data_dir

    def switch_dir(self, path: Path) -> None:
        """
        Switch the brightway2 project directory to the given path.
        """
        # change the paths to the given dir
        if not isinstance(path, Path):
            path = Path(path)

        projects._base_data_dir = path
        projects._base_logs_dir = path / "logs"
        projects._base_logs_dir.mkdir(exist_ok=True, parents=True)

        # open (or otherwise create) the projects.db at the given location
        projects.db = SubstitutableDatabase(
            projects._base_data_dir / "projects.db", [ProjectDataset]
        )

        # emit that the current project has changed through the qUpdater
        qprojects.emitLater("current_changed")


projects: ProjectManager = projects
