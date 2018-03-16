# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore

from activity_browser.app.controller import Controller


def test_new_project(qtbot, mock, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    mock.patch.object(Controller, 'get_new_project_name', return_value='pytest_project_del')
    qtbot.mouseClick(
        ab_app.main_window.right_panel.project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project_del'


def test_change_project(qtbot, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    assert bw.projects.current == 'pytest_project_del'
    combobox = ab_app.main_window.right_panel.project_tab.projects_widget.projects_list
    assert 'default' in bw.projects
    assert 'default' in combobox.project_names
    combobox.activated.emit(combobox.project_names.index('default'))
    assert bw.projects.current == 'default'
    combobox.activated.emit(combobox.project_names.index('pytest_project_del'))
    assert bw.projects.current == 'pytest_project_del'


def test_delete_project(qtbot, mock, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    assert bw.projects.current == 'pytest_project_del'
    mock.patch.object(Controller, 'confirm_project_deletion', return_value=True)
    qtbot.mouseClick(
        ab_app.main_window.right_panel.project_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'default'
