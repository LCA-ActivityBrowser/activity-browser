"""
Product vs waste classification and drop-link LCA impacts (sqlite + functional_sqlite).

One ``@bw2test`` project per backend: classification, ``get_exchange_type``, and the
eight LCA scores share a single inventory build.
"""

from __future__ import annotations

import bw2calc as bc
import bw2data as bd
import bw_functional as bf
import pytest
from bw2data.tests import bw2test

from activity_browser.bwutils.commontasks import (
    get_exchange_type,
    is_node_product,
    is_node_waste,
)
from fixtures.bw_helpers import write_functional_database, write_method
from fixtures.product_waste_links import (
    CO2_OWN,
    EXPECTED_SCORES,
    LINK_SPECS,
    WASTE_HOSTS,
)

DB = "pw"
METHOD = ("pw_co2",)
CO2 = (DB, "CO2")

SQLITE_DROP_CASES = (
    ("W", True, "technosphere", -1.0),
    ("W", False, "substitution", -1.0),
    ("P", False, "technosphere", 1.0),
    ("P", True, "substitution", 1.0),
)
FUNCTIONAL_DROP_CASES = (
    ("w", True, "technosphere", -1.0),
    ("w", False, "substitution", -1.0),
    ("p", False, "technosphere", 1.0),
    ("p", True, "substitution", 1.0),
)


def _parse_drop_exchange(dragged_key: tuple, output: bool) -> tuple[str, float]:
    """Map ``get_exchange_type`` to (type, amount) as ``ExchangesTab.dropEvent`` does."""
    exc_type = get_exchange_type(dragged_key, output=output)
    assert exc_type is not None
    if exc_type.startswith("-"):
        return exc_type[1:], -1.0
    return exc_type, 1.0


def _add_drop_link(host_key: tuple, dragged_key: tuple, output: bool) -> None:
    exc_type, amount = _parse_drop_exchange(dragged_key, output)
    host = bd.get_activity(host_key)
    host.new_exchange(input=dragged_key, type=exc_type, amount=amount).save()


def _fu_demand(fu_key: tuple) -> dict:
    if is_node_waste(fu_key):
        return {fu_key: -1.0}
    return {fu_key: 1.0}


def _score(fu_key: tuple) -> float:
    lca = bc.LCA(_fu_demand(fu_key), METHOD)
    lca.lci()
    lca.lcia()
    return float(lca.score)


def _sqlite_base_nodes() -> dict:
    nodes = {
        CO2: {
            "name": "Carbon dioxide",
            "type": "emission",
            "unit": "kg",
            "categories": ("air",),
            "exchanges": [],
        },
    }
    for code, co2 in CO2_OWN.items():
        is_waste = code in WASTE_HOSTS
        nodes[(DB, code)] = {
            "name": code,
            "type": "processwithreferenceproduct",
            "unit": "kg",
            "location": "GLO",
            "reference product": code.lower(),
            "exchanges": [
                {
                    "input": (DB, code),
                    "type": "production",
                    "amount": -1.0 if is_waste else 1.0,
                },
                {"input": CO2, "type": "biosphere", "amount": co2},
            ],
        }
    return nodes


def _functional_base_nodes() -> dict:
    nodes = {
        CO2: {
            "name": "Carbon dioxide",
            "code": "CO2",
            "type": "emission",
            "unit": "kg",
            "categories": ("air",),
            "exchanges": [],
        },
    }
    for code, co2 in CO2_OWN.items():
        is_waste = code in WASTE_HOSTS
        flow_code = code.lower()
        nodes[(DB, flow_code)] = {
            "name": flow_code,
            "type": "waste" if is_waste else "product",
            "unit": "kg",
            "location": "GLO",
            "processor": (DB, code),
            "exchanges": [],
        }
        nodes[(DB, code)] = {
            "name": code,
            "type": "process",
            "location": "GLO",
            "exchanges": [
                {
                    "input": (DB, flow_code),
                    "type": "production",
                    "amount": -1.0 if is_waste else 1.0,
                },
                {"input": CO2, "type": "biosphere", "amount": co2},
            ],
        }
    return nodes


def _assert_drop_cases(cases: tuple) -> None:
    for drag_code, output, expected_type, expected_amount in cases:
        got_type, got_amount = _parse_drop_exchange((DB, drag_code), output)
        assert got_type == expected_type, drag_code
        assert got_amount == expected_amount, drag_code


@bw2test
def test_sqlite_product_waste_links():
    # Missing production → product (before writing the full inventory)
    bd.Database(DB).write(
        {
            (DB, "X"): {
                "name": "X",
                "type": "processwithreferenceproduct",
                "unit": "kg",
                "location": "GLO",
                "reference product": "x",
                "exchanges": [],
            }
        }
    )
    assert is_node_product((DB, "X"))
    assert not is_node_waste((DB, "X"))

    bd.Database(DB).write(_sqlite_base_nodes())

    assert is_node_product((DB, "P")) and not is_node_waste((DB, "P"))
    assert is_node_waste((DB, "W")) and not is_node_product((DB, "W"))
    assert is_node_product((DB, "A"))
    assert is_node_waste((DB, "B"))
    _assert_drop_cases(SQLITE_DROP_CASES)

    for host, dragged, on_output in LINK_SPECS:
        _add_drop_link((DB, host), (DB, dragged), on_output)
    bd.Database(DB).process()
    write_method(METHOD[0], [(CO2, 1.0)], process=True)

    for host_code, expected in EXPECTED_SCORES.items():
        assert _score((DB, host_code)) == pytest.approx(expected), host_code


@bw2test
def test_functional_product_waste_links():
    write_functional_database(DB, _functional_base_nodes(), process=True)

    assert is_node_product((DB, "p")) and not is_node_waste((DB, "p"))
    assert is_node_waste((DB, "w")) and not is_node_product((DB, "w"))
    _assert_drop_cases(FUNCTIONAL_DROP_CASES)

    for host, dragged, on_output in LINK_SPECS:
        _add_drop_link((DB, host), (DB, dragged.lower()), on_output)
    bf.FunctionalSQLiteDatabase(DB).process()
    write_method(METHOD[0], [(CO2, 1.0)], process=True)

    for host_code, expected in EXPECTED_SCORES.items():
        assert _score((DB, host_code.lower())) == pytest.approx(expected), host_code
