# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore

from activity_browser.app.controller import Controller
from activity_browser.app.signals import signals
from activity_browser.app.ui.db_import_wizard import import_signals


def test_add_default_data(qtbot, mock, ab_app):
    assert bw.projects.current == 'default'
    qtbot.waitForWindowShown(ab_app.main_window)
    mock.patch.object(Controller, 'get_new_project_name', return_value='pytest_project')
    qtbot.mouseClick(
        ab_app.main_window.right_panel.project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    with qtbot.waitSignal(import_signals.biosphere_finished, timeout=600000):
        qtbot.mouseClick(
            ab_app.main_window.right_panel.project_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )


def test_select_biosphere(ab_app):
    flows = ab_app.main_window.right_panel.project_tab.flows_widget
    assert flows.table.rowCount() == 0
    assert not flows.table.isVisible()
    db_table = ab_app.main_window.right_panel.project_tab.databases_widget.table
    dbs = [db_table.item(i, 0).text() for i in range(db_table.rowCount())]
    assert 'biosphere3' in dbs
    # TODO: ideally replace the signal below with qtbot.mouseDClick on the tableitem
    signals.database_selected.emit('biosphere3')
    assert flows.table.isVisible()
    assert flows.table.rowCount() > 0


def test_search_biosphere(qtbot, ab_app):
    assert bw.projects.current == 'pytest_project'
    flows = ab_app.main_window.right_panel.project_tab.flows_widget
    currently_displayed = flows.table.rowCount()
    qtbot.keyClicks(flows.search_box, 'Pentanol')
    flows.search_box.returnPressed.emit()
    search_results = flows.table.rowCount()
    assert search_results < currently_displayed
