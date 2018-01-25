# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore

from activity_browser.app.controller import Controller


def test_default_project():
    assert bw.projects.current == 'default'


def test_new_project(qtbot, mock, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    mock.patch.object(Controller, 'get_new_project_name', return_value='test_project')
    qtbot.mouseClick(
        ab_app.main_window.right_panel.inventory_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'test_project'


def test_delete_project(qtbot, mock, ab_app):
    qtbot.waitForWindowShown(ab_app.main_window)
    assert bw.projects.current == 'test_project'
    mock.patch.object(Controller, 'confirm_project_deletion', return_value=True)
    qtbot.mouseClick(
        ab_app.main_window.right_panel.inventory_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'default'
