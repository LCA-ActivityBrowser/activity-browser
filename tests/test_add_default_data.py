# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtCore, QtWidgets

from activity_browser.signals import signals


def test_add_default_data(qtbot, ab_app, monkeypatch):
    assert bw.projects.current == 'default'
    qtbot.waitForWindowShown(ab_app.main_window)
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText",
        staticmethod(lambda *args, **kwargs: ("pytest_project", True))
    )
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    qtbot.mouseClick(
        project_tab.projects_widget.new_project_button,
        QtCore.Qt.LeftButton
    )
    assert bw.projects.current == 'pytest_project'

    # The biosphere3 import finishes with a 'change_project' signal.
    with qtbot.waitSignal(signals.change_project, timeout=600000):
        qtbot.mouseClick(
            project_tab.databases_widget.add_default_data_button,
            QtCore.Qt.LeftButton
        )


def test_select_biosphere(qtbot, ab_app):
    """ Select the 'biosphere3' database from the databases table.
    """
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    act_bio_widget = project_tab.activity_biosphere_widget
    db_table = project_tab.databases_widget.table
    dbs = [
        db_table.model.index(i, 0).data() for i in range(db_table.rowCount())
    ]
    assert 'biosphere3' in dbs

    # Grab the rectangle of the 2nd column on the first row.
    rect = db_table.visualRect(db_table.proxy_model.index(0, 1))
    with qtbot.waitSignal(signals.database_selected, timeout=2000):
        # Click once to 'focus' the table
        qtbot.mouseClick(db_table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
        # Then double-click to trigger the `doubleClick` event.
        qtbot.mouseDClick(db_table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())

    assert act_bio_widget.table.rowCount() > 0


def test_search_biosphere(qtbot, ab_app):
    assert bw.projects.current == 'pytest_project'
    project_tab = ab_app.main_window.left_panel.tabs['Project']
    act_bio_widget = project_tab.activity_biosphere_widget
    initial_amount = act_bio_widget.table.rowCount()
    # Now search for a specific string
    with qtbot.waitSignal(act_bio_widget.search_box.returnPressed, timeout=1000):
        qtbot.keyClicks(act_bio_widget.search_box, 'Pentanol')
        qtbot.keyPress(act_bio_widget.search_box, QtCore.Qt.Key_Return)
    # We found some results!
    assert act_bio_widget.table.rowCount() > 0
    # And the table is now definitely smaller than it was.
    assert act_bio_widget.table.rowCount() < initial_amount


def test_fail_open_biosphere(ab_app):
    """ Specifically fail to open an activity tab for a biosphere flow
    """
    assert bw.projects.current == "pytest_project"
    activities_tab = ab_app.main_window.right_panel.tabs["Activity Details"]
    # Select any biosphere activity and emit signal to trigger opening the tab
    biosphere_flow = bw.Database("biosphere3").random()
    signals.safe_open_activity_tab.emit(biosphere_flow.key)
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
    activities_tab = ab_app.main_window.right_panel.tabs["Activity Details"]
    # Select the activity and emit signal to trigger opening the tab
    act = bw.get_activity(act_key)
    signals.safe_open_activity_tab.emit(act_key)
    assert len(activities_tab.tabs) == 1
    assert act_key in activities_tab.tabs
    # Current index of QTabWidget is changed by opening the tab
    index = activities_tab.currentIndex()
    assert act.get("name") == activities_tab.tabText(index)


def test_close_open_activity_tab(ab_app):
    """Closing the activity tab will also hide the Activity Details tab."""
    act_key = ("testdb", "act1")
    act = bw.get_activity(act_key)
    act_name = act.get("name")
    activities_tab = ab_app.main_window.right_panel.tabs["Activity Details"]

    # The tab should still be open from the previous test
    assert act_key in activities_tab.tabs
    index = activities_tab.currentIndex()
    assert act_name == activities_tab.tabText(index)

    # Now close the tab.
    activities_tab.close_tab_by_tab_name(act_key)
    # Check that the tab no longer exists, and that the activity details tab
    # is hidden.
    assert act_key not in activities_tab.tabs
    assert activities_tab.isHidden()
