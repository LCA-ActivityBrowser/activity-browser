"""Partition-plot layout and aggregation (no Qt)."""

from __future__ import annotations

import pytest

from activity_browser.bwutils.graph_traversal.engine import build_parent_child_map
from activity_browser.bwutils.graph_traversal.partition_plots import (
    aggregate_plot_segments,
    build_chain_layout,
    build_sunburst_rings,
    plot_click_target_uid,
)

from tests.graph_traversal_fakes import (
    _FakeTraversalState,
    _circular_ab_visits,
    _edge,
    _expand_chain_state,
    _node,
    _rf_supplier_tree,
    _simple_tree,
    _two_visits_different_suppliers,
)


def test_sunburst_rings_tier1_shares():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=1)
    assert len(rings) == 1
    ring = rings[0]
    shares = {w["unique_id"]: w["share"] for w in ring}
    assert shares[1] == pytest.approx(0.6)
    assert shares[2] == pytest.approx(0.4)


def test_sunburst_rings_sum_le_one_per_parent():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=2)
    # Check tier-2 ring: children of node 1 (C=3, D=2) should sum to 5/6
    ring2 = rings[1]
    parent1_wedges = [w for w in ring2 if w["parent_unique_id"] == 1]
    total_share = sum(w["share"] for w in parent1_wedges)
    assert total_share <= 1.0 + 1e-9


def test_sunburst_rings_no_other_wedges():
    """Partial child lists no longer produce synthetic 'other' wedges."""
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=2)
    for ring in rings:
        assert all(w.get("label") != "other" for w in ring)
        assert all(w["unique_id"] is not None for w in ring)


def test_sunburst_rings_max_depth_respected():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=1)
    assert len(rings) == 1


def test_sunburst_rings_empty_on_zero_total():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 0.0, max_depth=2)
    assert rings == []


def test_sunburst_rings_exact_children_only():
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 1.0),
        2: _node(2, 1, 4.0, 1.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=1)
    assert len(rings[0]) == 2


def test_chain_layout_tier0_only_reference_flow():
    nodes, edges = _rf_supplier_tree()
    segs = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    tier0 = [s for s in segs if s["tier"] == 0]
    tier1 = [s for s in segs if s["tier"] == 1]
    assert len(tier0) == 1
    assert tier0[0]["unique_id"] == 0
    assert {s["unique_id"] for s in tier1} == {1, 2}


def test_chain_layout_supply_chain_x_alignment():
    nodes, edges = _rf_supplier_tree()
    segs = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    rf = next(s for s in segs if s["unique_id"] == 0)
    children = [s for s in segs if s["tier"] == 1]
    assert rf["x0"] == pytest.approx(0.0)
    assert rf["x1"] == pytest.approx(1.0)
    assert children[0]["x0"] == pytest.approx(0.0)
    assert children[0]["x1"] == pytest.approx(0.6)
    assert children[1]["x0"] == pytest.approx(0.6)
    assert children[1]["x1"] == pytest.approx(0.9)


def test_chain_layout_respects_included_uids():
    nodes, edges = _rf_supplier_tree()
    segs = build_chain_layout(
        nodes,
        edges,
        10.0,
        max_depth=2,
        root_uid=-1,
        included_uids={0, 1},
    )
    assert {s["unique_id"] for s in segs} == {0, 1}
    rf = next(s for s in segs if s["unique_id"] == 0)
    child = next(s for s in segs if s["unique_id"] == 1)
    assert rf["x0"] == pytest.approx(0.0)
    assert rf["x1"] == pytest.approx(1.0)
    assert child["x0"] == pytest.approx(0.0)
    # RF direct is 30% — sole visible child reflows within 70% upstream band.
    assert child["x1"] == pytest.approx(0.7)


def test_chain_layout_children_exclude_parent_direct():
    nodes, edges = _rf_supplier_tree()
    segs = build_chain_layout(
        nodes,
        edges,
        10.0,
        max_depth=2,
        root_uid=-1,
        included_uids={0, 1, 2},
    )
    rf = next(s for s in segs if s["unique_id"] == 0)
    children = sorted(
        (s for s in segs if s["tier"] == 1),
        key=lambda s: s["x0"],
    )
    assert rf["direct_pct"] == pytest.approx(30.0)
    assert children[-1]["x1"] == pytest.approx(0.7)


def test_chain_layout_negative_impact_has_positive_span():
    """Credits (negative cumulative) occupy layout space by magnitude; keep sign for colour."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 2.0, activity_id=100),
        1: _node(1, 2, 8.0, 1.0, activity_id=101),
        2: _node(2, 2, -2.0, -2.0, activity_id=102),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(0, 2)]
    segs = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    credit = next(s for s in segs if s["unique_id"] == 2)
    burden = next(s for s in segs if s["unique_id"] == 1)
    assert credit["x1"] > credit["x0"]
    assert credit["x1"] - credit["x0"] == pytest.approx(0.2)
    assert burden["x1"] - burden["x0"] == pytest.approx(0.8)
    assert credit["cumulative_score"] == pytest.approx(-2.0)
    assert credit["direct_pct"] == pytest.approx(-20.0)


def test_chain_layout_credit_when_parent_direct_exceeds_cumulative():
    """Visible-tree reflow: |direct| > |cumulative| must not collapse the credit band."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 16.667, activity_id=100),
        1: _node(1, 2, -6.667, -6.667, activity_id=101),
    }
    edges = [_edge(-1, 0), _edge(0, 1)]
    segs = build_chain_layout(
        nodes,
        edges,
        10.0,
        max_depth=2,
        root_uid=-1,
        included_uids={0, 1},
    )
    credit = next(s for s in segs if s["unique_id"] == 1)
    assert credit["x1"] - credit["x0"] == pytest.approx(0.6667, abs=1e-3)
    assert credit["direct_pct"] == pytest.approx(-66.67, abs=1e-2)


def test_plot_click_target_uid_uses_toggle_uid():
    assert plot_click_target_uid({"unique_id": 5, "toggle_uid": 2}) == 2
    assert plot_click_target_uid({"unique_id": 5}) == 5


def test_aggregate_plot_segments_merges_siblings_by_location():
    nodes, edges = _rf_supplier_tree()
    pcm = build_parent_child_map(nodes, edges)
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    for seg in segments:
        if seg["tier"] == 1:
            seg["location"] = "CH"
            seg["product"] = f"product-{seg['unique_id']}"
    merged = aggregate_plot_segments(segments, "location", pcm, -1, 10.0)
    tier1 = [s for s in merged if s["tier"] == 1]
    assert len(tier1) == 1
    assert tier1[0]["is_aggregate"] is True
    assert tier1[0]["toggle_uid"] == 0
    assert set(tier1[0]["constituent_uids"]) == {1, 2}
    assert tier1[0]["cumulative_score"] == pytest.approx(9.0)
    assert tier1[0]["direct_emissions_score"] == pytest.approx(2.0)
    assert tier1[0]["direct_pct"] == pytest.approx(20.0)
    assert tier1[0]["x0"] == pytest.approx(0.0)
    assert tier1[0]["x1"] == pytest.approx(0.7)


def test_aggregate_plot_segments_unknown_bucket():
    nodes, edges = _rf_supplier_tree()
    pcm = build_parent_child_map(nodes, edges)
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    for seg in segments:
        if seg["unique_id"] == 1:
            seg["location"] = ""
    merged = aggregate_plot_segments(segments, "location", pcm, -1, 10.0)
    keys = {
        s.get("aggregate_key")
        for s in merged
        if s["tier"] == 1 and s.get("is_aggregate")
    }
    assert "(unknown)" in keys or any(
        s["unique_id"] == 1 and s.get("aggregate_key") == "(unknown)"
        for s in merged
        if s["tier"] == 1
    )


def test_aggregate_plot_segments_none_preserves_segments():
    nodes, edges = _rf_supplier_tree()
    pcm = build_parent_child_map(nodes, edges)
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    out = aggregate_plot_segments(segments, None, pcm, -1, 10.0)
    assert len(out) == len(segments)
    assert all(not s.get("is_aggregate") for s in out)
    assert all(s["toggle_uid"] == s["unique_id"] for s in out)
