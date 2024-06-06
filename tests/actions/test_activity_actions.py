import pytest
import bw2data as bd
from PySide2 import QtWidgets

from activity_browser import actions
from activity_browser.mod.bw2data import Database
from activity_browser.ui.widgets.dialog import LocationLinkingDialog, ActivityLinkingDialog


def test_activity_delete(ab_app, monkeypatch):
    key = ('activity_tests', '330b935a46bc4ad39530ab7df012f38b')

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'warning',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    )

    assert bd.projects.current == "default"
    assert bd.get_activity(key)

    actions.ActivityDelete.run([key])

    with pytest.raises(Exception): bd.get_activity(key)


def test_activity_duplicate(ab_app):
    key = ('activity_tests', 'dd4e2393573c49248e7299fbe03a169c')
    dup_key = ('activity_tests', 'dd4e2393573c49248e7299fbe03a169c_copy1')

    assert bd.projects.current == "default"
    assert bd.get_activity(key)
    with pytest.raises(Exception): bd.get_activity(dup_key)

    actions.ActivityDuplicate.run([key])

    assert bd.get_activity(key)
    assert bd.get_activity(dup_key)


def test_activity_duplicate_to_db(ab_app, monkeypatch):
    key = ('activity_tests', 'dd4e2393573c49248e7299fbe03a169c')
    dup_key = ('db_to_duplicate_to', 'dd4e2393573c49248e7299fbe03a169c_copy1')

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getItem',
        staticmethod(lambda *args, **kwargs: ('db_to_duplicate_to', True))
    )

    assert bd.projects.current == "default"
    assert bd.get_activity(key)
    with pytest.raises(Exception): bd.get_activity(dup_key)

    actions.ActivityDuplicateToDB.run([key])

    assert bd.get_activity(key)
    assert bd.get_activity(dup_key)


def test_activity_duplicate_to_loc(ab_app, monkeypatch):
    key = ('activity_tests', 'dd4e2393573c49248e7299fbe03a169c')
    dup_key = ('activity_tests', 'dd4e2393573c49248e7299fbe03a169c_copy2')

    monkeypatch.setattr(
        LocationLinkingDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: True)
    )

    monkeypatch.setattr(
        LocationLinkingDialog, 'relink',
        {"MOON": "GLO"}
    )

    assert bd.projects.current == "default"
    assert bd.get_activity(key).as_dict()["location"] == "MOON"
    with pytest.raises(Exception): bd.get_activity(dup_key)

    actions.ActivityDuplicateToLoc.run(key)

    assert bd.get_activity(key).as_dict()["location"] == "MOON"
    assert bd.get_activity(dup_key).as_dict()["location"] == "GLO"


def test_activity_graph(ab_app):
    key = ('activity_tests', '3fcde3e3bf424e97b32cf29347ac7f33')
    panel = ab_app.main_window.right_panel.tabs["Graph Explorer"]

    assert bd.projects.current == "default"
    assert bd.get_activity(key)
    assert key not in panel.tabs

    actions.ActivityGraph.run([key])

    assert key in panel.tabs


def test_activity_new(ab_app, monkeypatch):
    database_name = "activity_tests"
    records = len(Database(database_name))

    monkeypatch.setattr(
        QtWidgets.QInputDialog, 'getText',
        staticmethod(lambda *args, **kwargs: ('activity_that_is_new', True))
    )

    actions.ActivityNew.run(database_name)

    assert records < len(Database(database_name))


def test_activity_open(ab_app):
    key = ('activity_tests', '3fcde3e3bf424e97b32cf29347ac7f33')
    panel = ab_app.main_window.right_panel.tabs["Activity Details"]

    assert bd.projects.current == "default"
    assert bd.get_activity(key)
    assert key not in panel.tabs

    actions.ActivityOpen.run([key])

    assert key in panel.tabs
    assert panel.isVisible()


def test_activity_relink(ab_app, monkeypatch, qtbot):
    key = ('activity_tests', '834c9010dff24c138c8ffa19924e5935')
    from_key = ('db_to_relink_from', '6a98a991da90495ea599e35b3d3602ab')
    to_key = ('db_to_relink_to', '0d4d83e3baee4b7e865c34a16a63f03e')

    monkeypatch.setattr(
        ActivityLinkingDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: True)
    )

    monkeypatch.setattr(
        ActivityLinkingDialog, 'relink',
        {"db_to_relink_from": "db_to_relink_to"}
    )

    assert bd.projects.current == "default"
    assert list(bd.get_activity(key).exchanges())[1].input.key == from_key

    actions.ActivityRelink.run([key])

    assert list(bd.get_activity(key).exchanges())[1].input.key == to_key
