import bw2data.project as project

import os

from bw2data.backends.peewee import SubstitutableDatabase

from activity_browser.signals import projects_updater
from ..patching import patch_superclass, patched


@patch_superclass
class ProjectManager(project.ProjectManager):

    @property
    def current_changed(self):
        return projects_updater.current_changed

    @property
    def list_changed(self):
        return projects_updater.list_changed

    def set_current(self, name, writable=True, update=True):
        patched().set_current(name, writable, update)
        projects_updater.emitLater("current_changed")

    def create_project(self, name=None, **kwargs):
        patched().create_project(name, **kwargs)
        projects_updater.emitLater("list_changed")

    def copy_project(self, new_name, switch=True):
        patched().copy_project(new_name, switch)
        projects_updater.emitLater("list_changed")

    def delete_project(self, name=None, delete_dir=False):
        patched().delete_project(name, delete_dir)
        projects_updater.emitLater("list_changed")

    # extending functionality
    @property
    def base_dir(self) -> str:
        return projects._base_data_dir

    def switch_dir(self, path: str) -> None:
        projects._base_data_dir = path
        projects._base_logs_dir = os.path.join(path, "logs")
        if not os.path.isdir(projects._base_logs_dir):
            os.mkdir(projects._base_logs_dir)

        projects.db = SubstitutableDatabase(
            os.path.join(projects._base_data_dir, "projects.db"),
            [project.ProjectDataset]
        )

        projects_updater.emitLater("current_changed")


projects: ProjectManager = project.projects
