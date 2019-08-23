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
    """ Select the 'biosphere3' database from the databases table.
    """
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    act_bio_widget = project_tab.activity_biosphere_widget
    db_table = project_tab.databases_widget.table
    dbs = [
        db_table.model.data(db_table.model.index(i, 0), QtCore.Qt.DisplayRole)
        for i in range(db_table.rowCount())
    ]
    assert 'biosphere3' in dbs
    # TODO: ideally replace the signal below with qtbot.mouseDClick on the tableitem
    # Sadly, there is no simple way of determining where to click to get the
    # correct row. Example here can be used for precise clicking:
    # https://github.com/pytest-dev/pytest-qt/issues/27#issuecomment-61897655
    signals.database_selected.emit('biosphere3')
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


def test_fail_open_biosphere(ab_app):
    """ Specifically fail to open an activity tab for a biosphere flow
    """
    assert bw.projects.current == "pytest_project"
    activities_tab = ab_app.main_window.right_panel.tabs["Activities"]
    # Select any biosphere activity and emit signal to trigger opening the tab
    biosphere_flow = bw.Database("biosphere3").random()
    signals.open_activity_tab.emit(biosphere_flow.key)
    assert len(activities_tab.tabs) == 0


def test_succceed_open_activity(ab_app):
    """ Create a tiny test database with a production activity
    """
    assert bw.projects.current == "pytest_project"
    db = bw.Database("testdb")
    act_key = ("testdb", "act1")
    db.write({
        act_key: {
            "name": "act1",
            "unit": "kilogram",
            "exchanges": [
                {"input": act_key, "amount": 1, "type": "production"}
            ]
        }
    })
    activities_tab = ab_app.main_window.right_panel.tabs["Activities"]
    # Select the activity and emit signal to trigger opening the tab
    act = bw.get_activity(act_key)
    signals.open_activity_tab.emit(act_key)
    assert len(activities_tab.tabs) == 1
    assert act_key in activities_tab.tabs
    # Current index of QTabWidget is changed by opening the tab
    index = activities_tab.currentIndex()
    assert act.get("name") == activities_tab.tabText(index)
