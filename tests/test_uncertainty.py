# -*- coding: utf-8 -*-
"""
Use the existing parameters to look at the uncertainty and edit it in
multiple ways
"""
import brightway2 as bw
from PySide2 import QtCore, QtWidgets
import pytest
from stats_arrays.distributions import UndefinedUncertainty, UniformUncertainty

from activity_browser.bwutils.uncertainty import (
    ExchangeUncertaintyInterface, CFUncertaintyInterface, get_uncertainty_interface
)
from activity_browser.ui.tables.delegates import UncertaintyDelegate
from activity_browser.ui.tables.parameters import ProjectParameterTable


def test_table_uncertainty_delegate(qtbot, bw2test, monkeypatch):
    """ Open the uncertainty delegate to test all related methods within the table.
    """
    table = ProjectParameterTable()
    qtbot.addWidget(table)
    bw.parameters.new_project_parameters([{"name": "project_1", "amount": 1.0}], False)
    table.model.sync()

    assert isinstance(table.itemDelegateForColumn(4), UncertaintyDelegate)

    delegate = UncertaintyDelegate(table)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 100, 100)
    index = table.proxy_model.index(0, 4)
    rect = table.visualRect(index)
    qtbot.mouseClick(table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    editor = delegate.createEditor(table, option, index)
    qtbot.addWidget(editor)

    # Test displayText
    assert delegate.displayText("1", None) == "No uncertainty"
    assert delegate.displayText("nan", None) == "Undefined or unknown uncertainty"

    delegate.setEditorData(editor, index)
    delegate.setModelData(editor, table.proxy_model, index)

    monkeypatch.setattr(QtCore.QModelIndex, "data", lambda *args, **kwargs: "nan")
    delegate.setEditorData(editor, index)


def test_exchange_interface(qtbot, ab_app):
    flow = bw.Database(bw.config.biosphere).random()
    db = bw.Database("testdb")
    act_key = ("testdb", "act_unc")
    db.write({
        act_key: {
            "name": "act_unc",
            "unit": "kilogram",
            "exchanges": [
                {"input": act_key, "amount": 1, "type": "production"},
                {"input": flow.key, "amount": 2, "type": "biosphere"},
            ]
        }
    })

    act = bw.get_activity(act_key)
    exc = next(e for e in act.biosphere())
    interface = get_uncertainty_interface(exc)
    assert isinstance(interface, ExchangeUncertaintyInterface)
    assert interface.amount == 2
    assert interface.uncertainty_type == UndefinedUncertainty
    assert interface.uncertainty == {}


@pytest.mark.xfail(reason="Selected CF was already uncertain")
def test_cf_interface(qtbot, ab_app):
    key = bw.methods.random()
    method = bw.Method(key).load()
    cf = next(f for f in method)

    assert isinstance(cf, tuple)
    if isinstance(cf[-1], dict):
        cf = method[1]
    assert isinstance(cf[-1], float)
    amount = cf[-1]  # last value in the CF should be the amount.

    interface = get_uncertainty_interface(cf)
    assert isinstance(interface, CFUncertaintyInterface)
    assert not interface.is_uncertain  # CF should not be uncertain.
    assert interface.amount == amount
    assert interface.uncertainty_type == UndefinedUncertainty
    assert interface.uncertainty == {}

    # Now add uncertainty.
    uncertainty = {"minimum": 1, "maximum": 18, "uncertainty type": UniformUncertainty.id}
    uncertainty["amount"] = amount
    cf = (cf[0], uncertainty)
    interface = get_uncertainty_interface(cf)
    assert isinstance(interface, CFUncertaintyInterface)
    assert interface.is_uncertain  # It is uncertain now!
    assert interface.amount == amount
    assert interface.uncertainty_type == UniformUncertainty
    assert interface.uncertainty == {"uncertainty type": UniformUncertainty.id, "minimum": 1, "maximum": 18}
