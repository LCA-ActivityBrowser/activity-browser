"""Tests for creating elementary flows."""

from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.activity import new_elementary_flow as mod
from activity_browser.bwutils.commontasks import get_writable_databases, is_node_biosphere


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


def _make_database_writable(db_name: str) -> None:
    import bw2data as bd

    bd.databases[db_name]["read_only"] = False
    bd.databases.flush()


def test_writable_databases_includes_basic(basic_database):
    _make_database_writable(basic_database.name)
    assert "basic" in get_writable_databases()


def test_activity_new_elementary_flow(basic_database, monkeypatch):
    _make_database_writable(basic_database.name)
    monkeypatch.setattr(mod, "NewElementaryFlowDialog", _AcceptedDialog)

    app.actions.NewElementaryFlow.run(database_name="basic")

    flows = [
        node
        for node in basic_database
        if node.get("name") == "custom emission" and is_node_biosphere(node)
    ]
    assert len(flows) == 1
    flow = flows[0]
    assert flow["type"] == "emission"
    assert flow["unit"] == "kg"
    assert flow["categories"] == ("air", "custom")
