"""Tests for creating elementary flows."""

from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.activity import new_elementary_flow as mod
from activity_browser.bwutils.commontasks import get_writable_databases


class _AcceptedDialog:
    def __init__(self, *args, **kwargs):
        pass

    def exec_(self):
        return QtWidgets.QDialog.DialogCode.Accepted

    def get_data(self):
        return ("basic", "custom emission", "kg", "emission", ("air", "custom"))


def test_parse_categories():
    assert mod._parse_categories("") == ()
    assert mod._parse_categories("air, non-urban") == ("air", "non-urban")


def test_writable_databases_includes_basic(basic_database):
    assert "basic" in get_writable_databases()


def test_activity_new_elementary_flow(basic_database, monkeypatch):
    monkeypatch.setattr(mod, "NewElementaryFlowDialog", _AcceptedDialog)

    app.actions.NewElementaryFlow.run(database_name="basic")

    flow = next(
        node for node in basic_database if node.get("name") == "custom emission"
    )
    assert flow["type"] == "emission"
    assert flow["unit"] == "kg"
    assert flow["categories"] == ("air", "custom")


def test_activity_new_elementary_flow_links_process(basic_database, monkeypatch):
    monkeypatch.setattr(mod, "NewElementaryFlowDialog", _AcceptedDialog)

    process = basic_database.get("process")
    app.actions.NewElementaryFlow.run(link_to_process=process.key)

    flow = next(
        node for node in basic_database if node.get("name") == "custom emission"
    )
    linked = [exc for exc in process.biosphere() if exc.input.key == flow.key]
    assert len(linked) == 1
