# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore

from activity_browser.app.controller import Controller
from activity_browser.app.ui.db_import_wizard import import_signals


def test_add_default_data(qtbot, mock, ab_app):
    assert bw.projects.current == 'default'
    qtbot.waitForWindowShown(ab_app.main_window)
    mock.patch.object(Controller, 'get_new_project_name', return_value='pytest_project')
    qtbot.mouseClick(
        ab_app.main_window.right_panel.inventory_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    with qtbot.waitSignal(import_signals.biosphere_finished, timeout=600000):
        qtbot.mouseClick(
            ab_app.main_window.right_panel.inventory_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )
