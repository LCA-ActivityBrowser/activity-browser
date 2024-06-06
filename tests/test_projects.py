# -*- coding: utf-8 -*-
from bw2data.project import projects

from PySide2 import QtCore, QtWidgets

from activity_browser.ui.widgets.dialog import ProjectDeletionDialog


def test_new_project(qtbot, ab_app, monkeypatch):
    qtbot.waitForWindowShown(ab_app.main_window)
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText",
        staticmethod(lambda *args, **kwargs: ("pytest_project_del", True))
    )
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert projects.current == 'pytest_project_del'


def test_change_project(qtbot, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    assert projects.current == 'pytest_project_del'
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    combobox = project_tab.projects_widget.projects_list
    assert 'default' in projects
    assert 'default' in combobox.project_names
    combobox.activated.emit(combobox.project_names.index('default'))
    assert projects.current == 'default'
    combobox.activated.emit(combobox.project_names.index('pytest_project_del'))
    assert projects.current == 'pytest_project_del'


def test_delete_project(qtbot, ab_app, monkeypatch):
    qtbot.waitForWindowShown(ab_app.main_window)
    assert projects.current == 'pytest_project_del'
    monkeypatch.setattr(
        ProjectDeletionDialog, "exec_",
        staticmethod(lambda *args: ProjectDeletionDialog.Accepted)
    )
    monkeypatch.setattr(
        ProjectDeletionDialog, "deletion_warning_checked",
        staticmethod(lambda *args: True)
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information",
        staticmethod(lambda *args: True)
    )
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )

    assert projects.current == 'default'