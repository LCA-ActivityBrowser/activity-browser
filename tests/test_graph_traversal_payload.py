"""JSON payload for the contribution-tree / Sankey node-link renderer (no Qt).

Seam: engine ``d3_graph_payload`` is visit-based; ``sankey.d3_graph_payload``
collapses to one box per process. JavaScript must not recompute adjust policy.
"""

from __future__ import annotations

import json

import pytest

from activity_browser.bwutils.graph_traversal.engine import (
    d3_graph_payload,
    format_graph_edge_tooltip,
    format_impact_abs,
    open_process_activity_id,
    open_process_refs,
)
from activity_browser.bwutils.graph_traversal.sankey import (
    d3_graph_payload as sankey_graph_payload,
    merge_graph_edges,
)

from graph_traversal_fakes import _edge, _node, _rf_supplier_tree


def _lookup(activity_id):
    return {
        100: {
            "name": "steel production",
            "product": "steel",
            "location": "CH",
            "database": "ei",
            "code": "steel",
            "unit": "kg",
        },
        101: {
            "name": "electricity, medium voltage",
            "product": "electricity",
            "location": "CH",
            "database": "ei",
            "code": "elec",
            "unit": "kWh",
        },
        102: {
            "name": "heat production",
            "product": "heat",
            "location": "DE",
            "database": "ei",
            "code": "heat",
            "unit": "MJ",
        },
    }.get(activity_id, {})


def test_graph_payload_includes_only_display_set_visits():
    nodes, edges = _rf_supplier_tree()
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1},
        metadata_lookup=_lookup,
        visited={-1, 0, 1, 2},
    )
    ids = {n["id"] for n in payload["nodes"]}
    assert ids == {0, 1}
    assert payload["kind"] == "graph"
    assert {(e["source_id"], e["target_id"]) for e in payload["edges"]} == {(1, 0)}
    json.dumps(payload)


def test_graph_payload_direct_and_path_signs():
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 0.0, activity_id=100),
        1: _node(1, 2, 4.0, 2.0, activity_id=101),
        2: _node(2, 2, -1.0, -0.5, activity_id=102),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(0, 2)]
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2},
        metadata_lookup=_lookup,
        visited={-1, 0, 1, 2},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[0]["activity_id"] == 100
    assert by_id[1]["activity_id"] == 101
    assert by_id[2]["activity_id"] == 102
    assert by_id[1]["visit_id"] == 1
    assert by_id[1]["code"] == "elec"
    assert by_id[1]["database"] == "ei"
    assert by_id[0]["direct_sign"] == 0
    assert by_id[1]["direct_sign"] == 1
    assert by_id[2]["direct_sign"] == -1
    signs = {(e["source_id"], e["path_sign"]) for e in payload["edges"]}
    assert (1, 1) in signs
    assert (2, -1) in signs


def test_graph_payload_color_key_is_location_without_merging():
    nodes, edges = _rf_supplier_tree()
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2},
        metadata_lookup=_lookup,
        color_by="location",
        visited={-1, 0, 1, 2},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[1]["color_key"] == "CH"
    assert by_id[2]["color_key"] == "DE"
    assert {n["id"] for n in payload["nodes"]} == {0, 1, 2}


def test_graph_payload_omits_empty_location():
    nodes = {
        -1: _node(-1, 0, 5.0, 0.0),
        0: _node(0, 1, 5.0, 5.0, activity_id=999),
    }
    edges = [_edge(-1, 0)]
    payload = d3_graph_payload(
        nodes,
        edges,
        5.0,
        root_uid=-1,
        included_uids={0},
        metadata_lookup=lambda _aid: {"name": "orphan", "product": "x"},
        visited={-1, 0},
    )
    assert payload["nodes"][0]["location"] == ""
    assert "Location:" not in payload["nodes"][0]["tooltip"]


def test_graph_payload_hidden_suppliers_and_terminal():
    nodes, edges = _rf_supplier_tree()
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1},
        metadata_lookup=_lookup,
        visited={-1, 0, 1, 2},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[0]["has_hidden_suppliers"] is True
    assert by_id[0]["can_collapse"] is True
    assert by_id[0]["is_terminal"] is False
    assert by_id[1]["is_terminal"] is True
    assert by_id[1]["has_hidden_suppliers"] is False
    assert by_id[1]["can_collapse"] is False


def test_graph_payload_leaf_aggregate_hides_constituent_upstream():
    nodes, edges = _rf_supplier_tree()
    grandchild = _node(3, 3, 2.0, 2.0, activity_id=101)
    nodes[3] = grandchild
    edges = list(edges) + [_edge(1, 3)]

    def both_ch(activity_id):
        meta = dict(_lookup(activity_id) or {"name": "x", "product": "x"})
        meta["location"] = "CH"
        return meta

    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2, 3},
        metadata_lookup=both_ch,
        aggregate_by="location",
        visited={-1, 0, 1, 2, 3},
    )
    real_ids = {n["id"] for n in payload["nodes"] if not n.get("is_aggregate")}
    aggs = [n for n in payload["nodes"] if n.get("is_aggregate")]
    assert real_ids == {0}
    assert len(aggs) == 1
    agg = aggs[0]
    assert agg["aggregate_key"] == "CH"
    assert agg["toggle_uid"] == 0
    assert agg["click_uid"] == 0
    assert agg["is_terminal"] is True
    assert agg["has_hidden_suppliers"] is False
    assert agg["can_collapse"] is False
    assert 3 not in {n["id"] for n in payload["nodes"]}
    assert {(e["source_id"], e["target_id"]) for e in payload["edges"]} == {
        (agg["id"], 0)
    }
    json.dumps(payload)


def test_graph_payload_demand_class_and_sankey_fields():
    nodes, edges = _rf_supplier_tree()
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2},
        metadata_lookup=_lookup,
        unit="kg CO2-Eq",
        visited={-1, 0, 1, 2},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[0]["class"] == "demand"
    assert by_id[1]["class"] == "production"
    assert by_id[1]["direct_emissions_score_normalized"] == 0.1
    assert payload["edges"]
    assert all(e["class"] in {"impact", "benefit"} for e in payload["edges"])
    assert all(e["impact_unit"] == "kg CO2-Eq" for e in payload["edges"])


def _circular_ab_visits():
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 2.0, activity_id=100),
        1: _node(1, 2, 7.0, 1.0, activity_id=101),
        2: _node(2, 3, 5.0, 5.0, activity_id=100),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(1, 2)]
    # Cutoff-scale later visit of the same B→A flow should not replace the first.
    nodes[3] = _node(3, 4, 0.01, 0.01, activity_id=101)
    edges = list(edges) + [_edge(2, 3)]
    return nodes, edges


def test_graph_payload_unique_activities_keeps_two_cycle_boxes():
    nodes, edges = _circular_ab_visits()
    payload = sankey_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2, 3},
        metadata_lookup=_lookup,
        visited=set(nodes),
    )
    ids = {n["id"] for n in payload["nodes"]}
    assert ids == {0, 1}
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[0]["can_collapse"] is True
    assert by_id[1]["has_hidden_suppliers"] is False
    assert by_id[1]["can_collapse"] is False
    pairs = {(e["source_id"], e["target_id"]) for e in payload["edges"]}
    assert pairs == {(1, 0), (0, 1)}
    by_pair = {(e["source_id"], e["target_id"]): e for e in payload["edges"]}
    assert by_pair[(1, 0)]["impact_cumulative"] == pytest.approx(7.0)
    assert by_pair[(0, 1)]["impact_cumulative"] == pytest.approx(5.0)
    json.dumps(payload)


def test_graph_payload_unopened_visit_is_not_terminal():
    nodes, edges = _circular_ab_visits()
    payload = sankey_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1},
        metadata_lookup=_lookup,
        visited=set(nodes),
        opened_uids={-1, 0},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id[1]["is_terminal"] is False
    assert by_id[1]["has_hidden_suppliers"] is True


def test_graph_payload_hidden_uses_other_visit_suppliers():
    """Triangle on the large-path box when another visit of P still has a unique supplier."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 0.5, 0.1, activity_id=10),
        2: _node(2, 1, 36.0, 0.17, activity_id=10),
        3: _node(3, 2, 0.4, 0.4, activity_id=20),
        4: _node(4, 2, 30.0, 1.0, activity_id=30),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(1, 3), _edge(2, 4)]
    payload = sankey_graph_payload(
        nodes,
        edges,
        100.0,
        root_uid=-1,
        included_uids={2, 4},
        metadata_lookup=_lookup,
        visited=set(nodes),
        opened_uids={-1, 1, 2},
    )
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert 2 in by_id
    assert by_id[2]["has_hidden_suppliers"] is True
    assert by_id[2]["is_terminal"] is False


def test_merge_graph_edges_keeps_largest_flow_not_cutoff_tail():
    merged = merge_graph_edges([
        {"source_id": 1, "target_id": 0, "impact_cumulative": 7.0, "impact_pct_total": 70.0},
        {"source_id": 1, "target_id": 0, "impact_cumulative": 0.01, "impact_pct_total": 0.1},
        {"source_id": 0, "target_id": 1, "impact_cumulative": 5.0, "impact_pct_total": 50.0},
    ])
    by_pair = {(e["source_id"], e["target_id"]): e for e in merged}
    assert by_pair[(1, 0)]["impact_pct_total"] == 70.0
    assert by_pair[(0, 1)]["impact_pct_total"] == 50.0


def test_open_process_refs_prefer_visit_over_js_activity_id():
    nodes, _edges = _rf_supplier_tree()
    assert open_process_refs(activity_id=101) == [{"activity_id": 101}]
    assert open_process_refs(nodes=nodes, uid=1) == [{"activity_id": 101}]
    assert open_process_refs(nodes=nodes, uid="1", activity_id=999) == [
        {"activity_id": 101}
    ]
    assert open_process_refs(
        nodes=nodes,
        uid=1,
        database="ei",
        code="elec",
        activity_id=999,
    ) == [{"activity_id": 101, "database": "ei", "code": "elec"}]
    assert open_process_refs(is_aggregate=True, activity_id=101) == []
    assert open_process_refs(activity_id=-5) == []
    assert open_process_refs(nodes=nodes, uid=-1) == []
    assert open_process_refs(
        is_aggregate=True,
        constituent_uids=[1, 2],
        nodes=nodes,
    ) == []
    assert open_process_refs(database="ei", code="elec") == [
        {"database": "ei", "code": "elec"}
    ]
    assert open_process_activity_id(activity_id=101) == 101
    assert open_process_activity_id(nodes=nodes, uid=1) == 101
    assert open_process_activity_id(is_aggregate=True, activity_id=101) is None
    assert open_process_activity_id(
        is_aggregate=True, constituent_uids=[1], nodes=nodes
    ) is None


def test_graph_payload_edges_include_flow_amount_and_unit():
    nodes, edges = _rf_supplier_tree()
    nodes[1] = _node(1, 2, 6.0, 1.0, supply=3.5, activity_id=101)
    payload = d3_graph_payload(
        nodes,
        edges,
        10.0,
        root_uid=-1,
        included_uids={0, 1, 2},
        metadata_lookup=_lookup,
        visited={-1, 0, 1, 2},
        unit="kg CO2-Eq",
    )
    edge = next(e for e in payload["edges"] if e["source_id"] == 1)
    assert edge["amount"] == pytest.approx(3.5)
    assert edge["amount_unit"] == "kWh"
    assert "Flow amount: 3.500 kWh" in edge["tooltip"]
    assert "Path impact: 60.00%" in edge["tooltip"]
    assert "kg CO2-Eq" in edge["tooltip"]


def test_format_graph_edge_tooltip_matches_node_hover_numbers():
    text = format_graph_edge_tooltip({
        "product": "electricity",
        "amount": 0.0042,
        "amount_unit": "kWh",
        "impact_cumulative": 12.3456,
        "impact_pct_total": 12.3,
        "impact_unit": "kg CO2-Eq",
    })
    assert "Product: electricity" in text
    assert f"Flow amount: {format_impact_abs(0.0042)} kWh" in text
    assert f"Path impact: 12.30% ({format_impact_abs(12.3456)} kg CO2-Eq)" in text
