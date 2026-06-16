"""Tests for editing elementary flows."""

from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.activity import edit_elementary_flow as edit_mod
from activity_browser.bwutils.elementary_flows import create_elementary_flow
from activity_browser.bwutils.commontasks import is_node_biosphere


class _AcceptedDialog:
    def __init__(self, *args, **kwargs):
        pass

    def exec_(self):
        return QtWidgets.QDialog.DialogCode.Accepted

    def get_data(self):
        return ("edited emission", "tonne", "natural resource", ("water",))


def _make_database_writable(db_name: str) -> None:
    import bw2data as bd

    bd.databases[db_name]["read_only"] = False
    bd.databases.flush()


def test_activity_edit_elementary_flow(basic_database, monkeypatch):
    elementary = basic_database.get("elementary")
    original_id = elementary.id

    _make_database_writable(basic_database.name)
    monkeypatch.setattr(edit_mod, "ElementaryFlowDialog", _AcceptedDialog)

    app.actions.EditElementaryFlow.run([elementary.key])

    flow = basic_database.get("elementary")
    assert flow.id == original_id
    assert flow["name"] == "edited emission"
    assert flow["unit"] == "tonne"
    assert flow["type"] == "natural resource"
    assert is_node_biosphere(flow)
    assert flow["categories"] == ("water",)


def test_edit_elementary_flow_ignores_non_biosphere(basic_database, monkeypatch):
    process = basic_database.get("process")
    called = False

    def _fail_dialog(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(edit_mod, "ElementaryFlowDialog", _fail_dialog)

    app.actions.EditElementaryFlow.run([process.key])

    assert not called


def test_edit_elementary_flow_requires_single_biosphere_selection(basic_database, monkeypatch):
    elementary = basic_database.get("elementary")
    second = create_elementary_flow(
        basic_database.name,
        name="second",
        unit="kg",
        flow_type="emission",
    )
    _make_database_writable(basic_database.name)

    called = False

    def _fail_dialog(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(edit_mod, "ElementaryFlowDialog", _fail_dialog)

    app.actions.EditElementaryFlow.run([elementary.key, second.key])

    assert not called
