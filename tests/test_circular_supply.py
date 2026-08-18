"""Circular functional_sqlite inventory for Tree redo_lci and Sankey display."""

from __future__ import annotations

import bw2calc as bc
import bw2data as bd
import pytest
from bw2calc.errors import OutsideTechnosphere
from bw2data.tests import bw2test
from bw_graph_tools.graph_traversal import (
    GraphTraversalSettings,
    NewNodeEachVisitGraphTraversal,
    SameNodeEachVisitGraphTraversal,
)

from activity_browser.bwutils.contribution_tree import (
    d3_graph_payload,
    keep_best_visit_per_activity,
    overlay_inventory_directs,
    suppress_graph_traversal_warnings,
)
from activity_browser.bwutils.lca_inputs import prepared_lca_inputs
from fixtures.bw_helpers import write_functional_database, write_method

DB = "cycle"
METHOD = ("cycle_co2",)
CO2 = (DB, "CO2")


def _cycle_nodes() -> dict:
    return {
        CO2: {
            "name": "Carbon dioxide",
            "code": "CO2",
            "type": "emission",
            "unit": "kg",
            "categories": ("air",),
            "exchanges": [],
        },
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
            "name": "A",
            "type": "process",
            "location": "GLO",
            "exchanges": [
                {"input": (DB, "a"), "type": "production", "amount": 1.0},
                {"input": (DB, "b"), "type": "technosphere", "amount": 0.9},
                {"input": CO2, "type": "biosphere", "amount": 1.0},
            ],
        },
        (DB, "B"): {
            "name": "B",
            "type": "process",
            "location": "GLO",
            "exchanges": [
                {"input": (DB, "b"), "type": "production", "amount": 1.0},
                {"input": (DB, "a"), "type": "technosphere", "amount": 0.9},
                {"input": CO2, "type": "biosphere", "amount": 1.0},
            ],
        },
    }


@bw2test
def test_circular_functional_sqlite_tree_and_sankey_calculate():
    write_functional_database(DB, _cycle_nodes(), process=True)
    write_method(METHOD[0], [(CO2, 1.0)], process=True)

    process_a = bd.get_activity((DB, "A"))
    process_b = bd.get_activity((DB, "B"))
    product_a = bd.get_activity((DB, "a"))
    assert process_a.id != product_a.id

    demand_ids = {process_a.id: 1.0}
    fu, data_objs, _ = prepared_lca_inputs(demand_ids, METHOD)
    assert product_a.id in fu
    assert process_a.id not in fu

    lca = bc.LCA(demand=fu, data_objs=data_objs)
    lca.lci(factorize=True)
    lca.lcia()
    assert lca.score > 0
    assert process_a.id not in lca.dicts.product
    assert product_a.id in lca.dicts.product

    with pytest.raises(OutsideTechnosphere):
        lca.redo_lci(demand_ids)

    lca.redo_lci(fu)
    lca.lcia()
    assert lca.score > 0

    state = SameNodeEachVisitGraphTraversal(
        lca=lca,
        settings=GraphTraversalSettings(cutoff=0.001, max_calc=50),
    )
    with suppress_graph_traversal_warnings():
        state.traverse(depth=5)
    tree_acts = {
        node.activity_datapackage_id
        for uid, node in state.nodes.items()
        if uid >= 0
    }
    assert len(tree_acts) == 2

    lca.redo_lci(fu)
    lca.lcia()
    data = NewNodeEachVisitGraphTraversal.calculate(
        lca_object=lca, cutoff=0.001, max_calc=50, max_depth=3
    )
    root = next(idx for idx in data["nodes"] if idx < 0)
    visits = [node for uid, node in data["nodes"].items() if uid >= 0]
    sankey_acts = {node.activity_datapackage_id for node in visits}
    assert len(sankey_acts) == 2
    assert len(visits) >= 2

    kept = keep_best_visit_per_activity(
        data["nodes"],
        data["edges"],
        {uid for uid in data["nodes"] if uid >= 0},
        root,
    )
    assert len(kept) == 2

    payload = d3_graph_payload(
        data["nodes"],
        data["edges"],
        float(lca.score),
        root_uid=root,
        included_uids=set(data["nodes"]),
        unique_activities=True,
        visited=set(data["nodes"]),
    )
    overlay_inventory_directs(payload, lca, float(lca.score))
    assert len(payload["nodes"]) == 2
    demand_node = next(n for n in payload["nodes"] if n.get("class") == "demand")
    other = next(n for n in payload["nodes"] if n.get("class") != "demand")
    assert demand_node["direct_pct"] == pytest.approx(100 / 1.9, abs=0.5)
    assert other["direct_pct"] == pytest.approx(90 / 1.9, abs=0.5)
    flow_pcts = sorted(abs(e["impact_pct_total"]) for e in payload["edges"])
    assert len(flow_pcts) == 2
    assert flow_pcts[0] != pytest.approx(flow_pcts[1], abs=0.05)
    assert min(flow_pcts) > 1.0
