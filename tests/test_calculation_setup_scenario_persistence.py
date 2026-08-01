"""Calculation-setup scenario persistence and column filtering."""

import pandas as pd

from activity_browser.bwutils.calculation_setup import (
    SCENARIO_AXES,
    SCENARIO_COMBINE,
    SCENARIO_INCLUDED,
    SCENARIO_PATHS,
    clear_scenario_persistence,
    filter_scenario_dataframe,
    get_scenario_persistence,
    reconcile_scenario_persistence,
    set_scenario_persistence,
)
from activity_browser.bwutils.superstructure.inclusion import MODE_PRODUCT
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE


def test_filter_scenario_dataframe_keeps_included_order():
    row = {c: None for c in SUPERSTRUCTURE}
    row.update(
        {
            "from key": ("db", "a"),
            "to key": ("db", "b"),
            "flow type": "technosphere",
            "A": 1.0,
            "B": 2.0,
            "C": 3.0,
        }
    )
    df = pd.DataFrame([row])
    # S order differs from file order; output must follow dataframe/file order.
    filtered = filter_scenario_dataframe(df, ["C", "A"])
    assert list(filtered.columns) == ["A", "C"]
    assert filtered.iloc[0]["C"] == 3.0


def test_get_set_clear_scenario_persistence(monkeypatch):
    store = {
        "cs": {
            "inv": [],
            "ia": [],
        }
    }

    class _CS:
        def __getitem__(self, name):
            return store[name]

        def __setitem__(self, name, value):
            store[name] = value

        def serialize(self):
            pass

    import activity_browser.bwutils.calculation_setup as mod

    monkeypatch.setattr(mod, "bd", type("B", (), {"calculation_setups": _CS()})())

    assert get_scenario_persistence(store["cs"]) is None
    set_scenario_persistence(
        "cs",
        paths=["/tmp/a.xlsx"],
        combine=MODE_PRODUCT,
        included=["A | X"],
        axes=[["A"], ["X"]],
    )
    got = get_scenario_persistence(store["cs"])
    assert got[SCENARIO_PATHS] == ["/tmp/a.xlsx"]
    assert got[SCENARIO_COMBINE] == MODE_PRODUCT
    assert got[SCENARIO_INCLUDED] == ["A | X"]
    assert got[SCENARIO_AXES] == [["A"], ["X"]]

    clear_scenario_persistence("cs")
    assert get_scenario_persistence(store["cs"]) is None


def test_reconcile_scenario_persistence_no_saved():
    result = reconcile_scenario_persistence({}, [["A"], ["X"]], MODE_PRODUCT)
    assert result.mismatched is False
    assert result.included == ["A | X"]
