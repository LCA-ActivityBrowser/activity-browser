# -*- coding: utf-8 -*-
"""
Use the existing parameters to look at the uncertainty and edit it in
multiple ways
"""
import bw2data as bd
import pytest
from stats_arrays.distributions import UndefinedUncertainty, UniformUncertainty

from activity_browser.bwutils.uncertainty import (CFUncertaintyInterface,
                                                  ExchangeUncertaintyInterface,
                                                  get_uncertainty_interface)
from activity_browser.mod.bw2data import Method, methods


def test_exchange_interface(qtbot, ab_app):
    bd.projects.set_current("default")
    flow = bd.Database(bd.config.biosphere).random()
    db = bd.Database("testdb")
    act_key = ("testdb", "act_unc")
    db.write(
        {
            act_key: {
                "name": "act_unc",
                "unit": "kilogram",
                "exchanges": [
                    {"input": act_key, "amount": 1, "type": "production"},
                    {"input": flow.key, "amount": 2, "type": "biosphere"},
                ],
            }
        }
    )

    act = bd.get_activity(act_key)
    exc = next(e for e in act.biosphere())
    interface = get_uncertainty_interface(exc)
    assert isinstance(interface, ExchangeUncertaintyInterface)
    assert interface.amount == 2
    assert interface.uncertainty_type == UndefinedUncertainty
    assert interface.uncertainty == {}


@pytest.mark.xfail(reason="Selected CF was already uncertain")
def test_cf_interface(qtbot, ab_app):
    key = methods.random()
    method = Method(key).load()
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
    uncertainty = {
        "minimum": 1,
        "maximum": 18,
        "uncertainty type": UniformUncertainty.id,
    }
    uncertainty["amount"] = amount
    cf = (cf[0], uncertainty)
    interface = get_uncertainty_interface(cf)
    assert isinstance(interface, CFUncertaintyInterface)
    assert interface.is_uncertain  # It is uncertain now!
    assert interface.amount == amount
    assert interface.uncertainty_type == UniformUncertainty
    assert interface.uncertainty == {
        "uncertainty type": UniformUncertainty.id,
        "minimum": 1,
        "maximum": 18,
    }
