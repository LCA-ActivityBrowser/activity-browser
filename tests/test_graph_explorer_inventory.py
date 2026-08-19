"""BrightwayInventory against a small functional_sqlite project."""

from __future__ import annotations

import bw2data as bd
from bw2data.tests import bw2test

from activity_browser.bwutils.graph_explorer.inventory import BrightwayInventory
from fixtures.bw_helpers import write_functional_database

DB = "geinv"


def _nodes() -> dict:
    return {
        (DB, "a"): {
            "name": "a",
            "type": "product",
            "unit": "kg",
            "location": "GLO",
            "processor": (DB, "A"),
            "exchanges": [],
        },
        (DB, "b"): {
            "name": "b",
            "type": "product",
            "unit": "kg",
            "location": "GLO",
            "processor": (DB, "B"),
            "exchanges": [],
        },
        (DB, "A"): {
            "name": "process A",
            "type": "process",
            "location": "GLO",
            "exchanges": [
                {"input": (DB, "a"), "type": "production", "amount": 1.0},
                {"input": (DB, "b"), "type": "technosphere", "amount": 0.5},
            ],
        },
        (DB, "B"): {
            "name": "process B",
            "type": "process",
            "location": "World",
            "exchanges": [
                {"input": (DB, "b"), "type": "production", "amount": 1.0},
            ],
        },
    }


@bw2test
def test_listed_technosphere_input_and_invalidate_clears_consumer_cache():
    write_functional_database(DB, _nodes(), process=True)
    host = bd.get_activity((DB, "A"))
    supplier = bd.get_activity((DB, "B"))
    inv = BrightwayInventory()
    listed = [
        c.process_id
        for key, _n in inv.flow_heads(host.id)
        for c in inv.counterparts_ranked(host.id, key)
        if c.from_exchange
    ]
    assert supplier.id in listed
    name, location = inv.label(host.id)
    assert name == "process A"
    assert location == "GLO"

    inv._consumer_count_cache[(DB, "a")] = 99
    inv.invalidate(host.id)
    assert inv._consumer_count_cache == {}
    listed_again = [
        c.process_id
        for key, _n in inv.flow_heads(host.id)
        for c in inv.counterparts_ranked(host.id, key)
        if c.from_exchange
    ]
    assert supplier.id in listed_again


def _substitution_nodes() -> dict:
    return {
        (DB, "heat"): {
            "name": "Heat production",
            "type": "product",
            "unit": "kilogram",
            "location": "GLO",
            "processor": (DB, "Heat"),
            "exchanges": [],
        },
        (DB, "elec"): {
            "name": "electricity",
            "type": "product",
            "unit": "kilowatt hour",
            "location": "GLO",
            "processor": (DB, "CHP"),
            "exchanges": [],
        },
        (DB, "chpheat"): {
            "name": "CHP heat",
            "type": "product",
            "unit": "megajoule",
            "location": "GLO",
            "processor": (DB, "CHP"),
            "exchanges": [],
        },
        (DB, "Heat"): {
            "name": "Heat production",
            "type": "process",
            "location": "GLO",
            "exchanges": [
                {"input": (DB, "heat"), "type": "production", "amount": 1.0},
            ],
        },
        (DB, "CHP"): {
            "name": "CHP - substitution",
            "type": "multifunctional",
            "location": "GLO",
            "exchanges": [
                {"input": (DB, "elec"), "type": "production", "amount": 1.0},
                {"input": (DB, "chpheat"), "type": "production", "amount": 0.0},
                {"input": (DB, "heat"), "type": "substitution", "amount": 1.0},
            ],
        },
    }


@bw2test
def test_substitution_link_from_chp_to_avoided_heat():
    write_functional_database(DB, _substitution_nodes(), process=True)
    chp = bd.get_activity((DB, "CHP"))
    heat = bd.get_activity((DB, "Heat"))
    inv = BrightwayInventory()
    from activity_browser.bwutils.graph_explorer.explorer import GraphExplorer

    ge = GraphExplorer(chp.id, inv)
    flows = [e for e in ge.payload()["edges"] if e["kind"] == "flow"]
    sub = next(e for e in flows if e["role"] == "substitution")
    assert sub["source_id"] == f"p:{chp.id}"
    assert sub["target_id"] == f"p:{heat.id}"
    assert sub["amount"] == 1.0
    assert sub["unit"] == "kilogram"

    ge2 = GraphExplorer(heat.id, inv)
    ge2.expand_side(heat.id, "downstream")
    flows2 = [e for e in ge2.payload()["edges"] if e["kind"] == "flow"]
    sub2 = next(e for e in flows2 if e["role"] == "substitution")
    assert sub2["source_id"] == f"p:{chp.id}"
    assert sub2["target_id"] == f"p:{heat.id}"
