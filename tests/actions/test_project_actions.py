import os.path

import bw2data as bd
from PySide2 import QtWidgets
from activity_browser import actions, ab_settings, application
from activity_browser.ui.widgets import ProjectDeletionDialog
from activity_browser.actions.project.project_export import ExportThread
from activity_browser.actions.project.project_import import ImportThread


def test_project_delete(ab_app, monkeypatch):
    project_name = "project_to_delete"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        ProjectDeletionDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: ProjectDeletionDialog.Accepted)
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'information',
        staticmethod(lambda *args, **kwargs: True)
    )

    assert bd.projects.current == project_name

    actions.ProjectDelete.run()

    assert bd.projects.current == ab_settings.startup_project
    assert project_name not in bd.projects

    actions.ProjectDelete.run()

    assert bd.projects.current == ab_settings.startup_project


def test_project_duplicate(ab_app, monkeypatch):
    project_name = "project_to_duplicate"
    dup_project_name = "duplicated_project"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: (dup_project_name, True))
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'information',
        staticmethod(lambda *args, **kwargs: True)
    )

    assert bd.projects.current == project_name
    assert dup_project_name not in bd.projects

    actions.ProjectDuplicate.run()

    assert bd.projects.current == dup_project_name
    assert project_name in bd.projects

    projects_number = len(bd.projects)

    actions.ProjectDuplicate.run()

    assert len(bd.projects) == projects_number


def test_project_new(ab_app, monkeypatch):
    project_name = "project_that_is_new"

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: (project_name, True))
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'information',
        staticmethod(lambda *args, **kwargs: True)
    )

    assert project_name not in bd.projects

    actions.ProjectNew.run()

    assert project_name in bd.projects

    projects_number = len(bd.projects)

    actions.ProjectNew.run()

    assert len(bd.projects) == projects_number

def test_project_export(ab_app, monkeypatch, qtbot):
    project_name = "default"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        QtWidgets.QFileDialog, 'getSaveFileName',
        staticmethod(lambda *args, **kwargs: (os.path.expanduser("~/default.tar.gz"), True))
    )

    assert not os.path.isfile(os.path.expanduser("~/default.tar.gz"))

    actions.ProjectExport.run()

    thread = application.findChild(ExportThread)
    with qtbot.waitSignal(thread.finished, timeout=5 * 60 * 1000): pass

    assert os.path.isfile(os.path.expanduser("~/default.tar.gz"))


def test_project_import(ab_app, monkeypatch, qtbot):
    """
    This currently does not work because of limitations in the bw2data testing mode i.e.: the in-memory projects sqlite
    db is not shared across threads.
    """
    return

    # project_name = "default"
    # bd.projects.set_current(project_name)
    #
    # monkeypatch.setattr(
    #     QtWidgets.QFileDialog, 'getOpenFileName',
    #     staticmethod(lambda *args, **kwargs: (os.path.expanduser("~/default.tar.gz"), True))
    # )
    #
    # monkeypatch.setattr(
    #     QtWidgets.QInputDialog, 'getText',
    #     staticmethod(lambda *args, **kwargs: (f"not_{project_name}", None))
    # )
    #
    # assert f"not_{project_name}" not in bd.projects
    # actions.ProjectImport.run()
    #
    # thread = application.findChild(ImportThread)
    # with qtbot.waitSignal(thread.finished, timeout=5 * 60 * 1000): pass
    #
    # assert bd.projects.current == f"not_{project_name}"


