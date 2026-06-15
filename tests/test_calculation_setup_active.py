"""Active flags and reordering for calculation setups."""

import pytest

from activity_browser.bwutils.calculation_setup import (
    INV_ACTIVE,
    IA_ACTIVE,
    active_flags,
    ensure_active_lists,
    move_rows,
)


@pytest.fixture
def cs_dict():
    return {
        "inv": [{"a": 1.0}, {"b": 2.0}, {"c": 3.0}],
        "ia": [("m1",), ("m2",)],
        "inv_active": [True, False, True],
        "ia_active": [True, True],
    }


def test_active_flags_defaults():
    cs = {"inv": [{"a": 1.0}], "ia": [("m",)]}
    assert active_flags(cs, "inv") == [True]


def test_active_subset(cs_dict):
    cs = dict(cs_dict)
    ensure_active_lists(cs)
    cs["inv"] = [fu for fu, ok in zip(cs["inv"], cs[INV_ACTIVE]) if ok]
    assert len(cs["inv"]) == 2


def test_move_rows():
    items = ["a", "b", "c", "d"]
    flags = [True, True, True, True]
    move_rows(items, flags, [1, 2], 0)
    assert items == ["b", "c", "a", "d"]
