# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore

from activity_browser.app.controller import Controller
from activity_browser.app.signals import signals
from activity_browser.app.ui.wizards.db_import_wizard import import_signals


def test_add_default_data(qtbot, mock, ab_app):
    assert bw.projects.current == 'default'
    qtbot.waitForWindowShown(ab_app.main_window)
    mock.patch.object(Controller, 'get_new_project_name_dialog', return_value='pytest_project')
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    with qtbot.waitSignal(import_signals.biosphere_finished, timeout=600000):
        qtbot.mouseClick(
            project_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )


def test_select_biosphere(ab_app):
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    act_bio_widget = project_tab.activity_biosphere_widget
    # assert act_bio_widget.table.rowCount() == 0
    # assert act_bio_widget.table.isHidden()
    db_table = project_tab.databases_widget.table
    dbs = [db_table.item(i, 0).text() for i in range(db_table.rowCount())]
    assert 'biosphere3' in dbs
    # TODO: ideally replace the signal below with qtbot.mouseDClick on the tableitem
    signals.database_selected.emit('biosphere3')
    # assert not act_bio_widget.table.isHidden()
    assert act_bio_widget.table.dataframe.shape[0] > 0


def test_search_biosphere(qtbot, ab_app):
    assert bw.projects.current == 'pytest_project'
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    act_bio_widget = project_tab.activity_biosphere_widget
    # currently_displayed = act_bio_widget.table.rowCount()
    qtbot.keyClicks(act_bio_widget.search_box, 'Pentanol')
    act_bio_widget.search_box.returnPressed.emit()
    assert act_bio_widget.table.dataframe.shape[0] > 0
    # assert search_results < currently_displayed
