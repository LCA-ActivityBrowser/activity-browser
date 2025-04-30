from bw2data.project import projects

from qtpy import QtWidgets

from activity_browser import actions
from activity_browser.actions.project.project_delete import ProjectDeletionDialog


def test_project_delete(ab_app, monkeypatch):
    project_name = "project_to_delete"
    projects.set_current(project_name)

    monkeypatch.setattr(
        ProjectDeletionDialog,
        "exec_",
        staticmethod(lambda *args, **kwargs: ProjectDeletionDialog.Accepted),
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert projects.current == project_name

    actions.ProjectDelete.run()

    assert projects.current == ab_settings.startup_project
    assert project_name not in projects

    actions.ProjectDelete.run()

    assert projects.current == ab_settings.startup_project


def test_project_duplicate(ab_app, monkeypatch):
    project_name = "project_to_duplicate"
    dup_project_name = "duplicated_project"
    projects.set_current(project_name)

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (dup_project_name, True)),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert projects.current == project_name
    assert dup_project_name not in projects

    actions.ProjectDuplicate.run()

    assert projects.current == dup_project_name
    assert project_name in projects

    projects_number = len(projects)

    actions.ProjectDuplicate.run()

    assert len(projects) == projects_number


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

    assert project_name not in projects

    actions.ProjectNew.run()

    assert project_name in projects

    projects_number = len(projects)

    actions.ProjectNew.run()

    assert len(projects) == projects_number
