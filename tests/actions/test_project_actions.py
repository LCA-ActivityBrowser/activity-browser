import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import ab_settings, actions
from activity_browser.ui.widgets import ProjectDeletionDialog


def test_project_delete(ab_app, monkeypatch):
    project_name = "project_to_delete"
    bw.projects.set_current(project_name)

    monkeypatch.setattr(
        ProjectDeletionDialog,
        "exec_",
        staticmethod(lambda *args, **kwargs: ProjectDeletionDialog.Accepted),
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert bw.projects.current == project_name

    actions.ProjectDelete.run()

    assert bw.projects.current == ab_settings.startup_project
    assert project_name not in bw.projects

    actions.ProjectDelete.run()

    assert bw.projects.current == ab_settings.startup_project


def test_project_duplicate(ab_app, monkeypatch):
    project_name = "project_to_duplicate"
    dup_project_name = "duplicated_project"
    bw.projects.set_current(project_name)

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (dup_project_name, True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert bw.projects.current == project_name
    assert dup_project_name not in bw.projects

    actions.ProjectDuplicate.run()

    assert bw.projects.current == dup_project_name
    assert project_name in bw.projects

    projects_number = len(bw.projects)

    actions.ProjectDuplicate.run()

    assert len(bw.projects) == projects_number


def test_project_new(ab_app, monkeypatch):
    project_name = "project_that_is_new"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (project_name, True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert project_name not in bw.projects

    actions.ProjectNew.run()

    assert project_name in bw.projects

    projects_number = len(bw.projects)

    actions.ProjectNew.run()

    assert len(bw.projects) == projects_number
