# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtCore, QtWidgets


def test_open_db_wizard(qtbot, ab_app):
    assert bw.projects.current == 'pytest_project'
    qtbot.waitForWindowShown(ab_app.main_window)
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.databases_widget.import_database_button,
        QtCore.Qt.LeftButton
    )
    qtbot.mouseClick(
        ab_app.controller.db_wizard.button(QtWidgets.QWizard.CancelButton),
        QtCore.Qt.LeftButton
    )
