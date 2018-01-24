# -*- coding: utf-8 -*-
import time

import brightway2 as bw
from PyQt5 import QtCore

from activity_browser import Application
from activity_browser.app.controller import Controller


def test_default_project():
    assert bw.projects.current == 'default'


def test_new_project(qtbot, mock):
    application = Application()
    qtbot.addWidget(application)
    application.show()
    qtbot.waitForWindowShown(application.main_window)
    time.sleep(1)
    mock.patch.object(Controller, 'get_new_project_name', return_value='test_project')
    qtbot.mouseClick(
        application.main_window.right_panel.inventory_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'test_project'


def test_delete_project(qtbot, mock):
    application = Application()
    qtbot.addWidget(application)
    application.show()
    qtbot.waitForWindowShown(application.main_window)
    time.sleep(1)
    assert bw.projects.current == 'test_project'
    mock.patch.object(Controller, 'confirm_project_deletion', return_value=True)
    qtbot.mouseClick(
        application.main_window.right_panel.inventory_tab.projects_widget.delete_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'default'
