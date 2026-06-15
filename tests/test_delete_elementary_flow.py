"""Tests for deleting elementary flows."""

from bw2data.errors import UnknownObject
from bw2data.method import Method
from qtpy import QtWidgets

import bw2data as bd

from activity_browser import app
from activity_browser.bwutils.characterization_factors import (
    impact_methods_with_flows,
    remove_characterization_factors_for_flows,
)


def _confirm_delete(monkeypatch) -> None:
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )


def _make_database_writable(db_name: str) -> None:
    bd.databases[db_name]["read_only"] = False
    bd.databases.flush()


def test_delete_elementary_flow_removes_cf_and_node(basic_database, monkeypatch):
    elementary = basic_database.get("elementary")
    flow_id = elementary.id
    flow_key = elementary.key

    _make_database_writable(basic_database.name)
    _confirm_delete(monkeypatch)

    app.actions.DeleteElementaryFlow.run([flow_key])

    try:
        bd.get_activity(flow_key)
        assert False, "elementary flow should be deleted"
    except UnknownObject:
        pass
    assert not [cf for cf in Method(("basic_method",)).load() if cf[0] == flow_id]
    assert len(list(basic_database.get("process").biosphere())) == 0


def test_remove_characterization_factors_for_flows(basic_database):
    elementary = basic_database.get("elementary")
    fake_id = 999999999999999
    method = Method(("basic_method",))
    method.write(list(method.load()) + [(fake_id, 1.0)], process=False)

    assert remove_characterization_factors_for_flows({elementary.id}) == 1
    ids = [cf[0] for cf in method.load()]
    assert elementary.id not in ids
    assert fake_id not in ids
    assert not impact_methods_with_flows({elementary.id})
