import shutil

from qtpy import QtWidgets

from bw2data.project import projects, ProjectDataset, safe_filename, create_dir

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ProjectMigrate25(ABAction):
    """
    ABAction to duplicate a project. Asks the user for a new name. Returns if no name is given, the user cancels, or
    when the name is already in use by another project. Else, instructs the ProjectController to duplicate the current
    project to the new name.
    """

    icon = qicons.copy
    text = "Migrate project"
    tool_tip = "Migrate the project to bw25"

    @staticmethod
    @exception_dialogs
    def run(name: str = None):
        if name is None:
            name = projects.current

        new_name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Migrate project",
            f"Migrate project ({name}) to Brightway25 project with name:"
            + " " * 10,
        )

        if not ok or not new_name:
            return

        if new_name in projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists.",
            )
            return

        ds = ProjectDataset.get(ProjectDataset.name == name)

        old_fp = projects._base_data_dir / safe_filename(ds.name, full=ds.full_hash)
        new_fp = projects._base_data_dir / safe_filename(new_name, full=ds.full_hash)
        if new_fp.exists():
            raise ValueError("Project directory already exists")

        ProjectDataset.create(data=ds.data, name=new_name, full_hash=ds.full_hash)

        shutil.copytree(old_fp, new_fp)
        create_dir(projects._base_logs_dir / safe_filename(new_name))

        projects.set_current(new_name)
        projects.migrate_project_25()
