from pathlib import Path
from types import SimpleNamespace

import bw2data as bd
from bw2data import config
from bw2data.parameters import ProjectParameter
from bw2data.project import ProjectDataset
from bw_processing import safe_filename
from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.project.project_delete import (
    ProjectDelete,
    ProjectDeletionDialog,
)


def _project_dir(name: str) -> Path:
    ds = ProjectDataset.get(ProjectDataset.name == name)
    return bd.projects._base_data_dir / safe_filename(name, full=ds.full_hash)


def _open_sqlite_files_in(dir_path: Path) -> list[str]:
    open_files = []
    for _, substitutable_db in config.sqlite3_databases:
        try:
            filepath = Path(substitutable_db._filepath)
            if filepath.is_relative_to(dir_path) and not substitutable_db.db.is_closed():
                open_files.append(str(filepath))
        except Exception:
            pass
    return open_files


def test_project_delete_closes_sqlite_before_removing_dir(monkeypatch, basic_database):
    """Windows cannot shutil.rmtree a project while parameters.db is still open."""
    original = bd.projects.current
    victim = "victim_project_to_delete"
    bd.projects.create_project(victim)
    bd.projects.set_current(victim, update=False)
    list(ProjectParameter.select())

    dir_path = _project_dir(victim)
    assert dir_path.is_dir()
    assert _open_sqlite_files_in(dir_path), "parameters.db / databases.db should be open"

    open_at_rmtree = []
    import activity_browser.app.actions.project.project_delete as project_delete_mod

    real_rmtree = project_delete_mod.shutil.rmtree

    def checking_rmtree(path, *args, **kwargs):
        open_at_rmtree.extend(_open_sqlite_files_in(Path(path)))
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(project_delete_mod.shutil, "rmtree", checking_rmtree)
    monkeypatch.setattr(
        project_delete_mod,
        "app",
        SimpleNamespace(
            signals=SimpleNamespace(
                project=SimpleNamespace(deleted=SimpleNamespace(emit=lambda *a, **k: None))
            )
        ),
    )

    try:
        ProjectDelete.delete_project(victim, True)
    finally:
        if original in bd.projects:
            bd.projects.set_current(original, update=False)

    assert open_at_rmtree == []
    assert victim not in bd.projects
    assert not dir_path.exists()


def test_project_delete_run_removes_current_project(monkeypatch, basic_database):
    monkeypatch.setattr(
        ProjectDeletionDialog, "exec_", lambda self: ProjectDeletionDialog.Accepted
    )
    monkeypatch.setattr(ProjectDeletionDialog, "deletion_warning_checked", lambda self: True)
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: None)
    )

    original = bd.projects.current
    victim = "victim_project_run_delete"
    bd.projects.create_project(victim)
    bd.projects.set_current(victim, update=False)
    list(ProjectParameter.select())
    dir_path = _project_dir(victim)

    monkeypatch.setitem(app.settings["startup"], "startup_project", original)
    ProjectDelete.run([victim])

    assert victim not in bd.projects
    assert not dir_path.exists()
    assert bd.projects.current == original
