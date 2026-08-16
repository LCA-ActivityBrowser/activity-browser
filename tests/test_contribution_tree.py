"""Tests for bwutils.contribution_tree data helpers.

All tests use plain SimpleNamespace fake objects — no Qt, no Brightway project.
Pattern follows tests/test_contribution_normalize.py and test_lcia_overview.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from activity_browser.bwutils.contribution_tree import (
    activity_metadata_for_ids,
    aggregate_plot_segments,
    build_chain_layout,
    build_parent_child_map,
    build_sunburst_rings,
    coverage_of_uids,
    cumulative_percent,
    direct_impact_intensity,
    direct_impact_coverage,
    direct_percent,
    flatten_to_dataframe,
    next_expand_candidates,
    plot_click_target_uid,
    is_terminal_node,
    path_display_set,
    plan_cumulative_expand,
    run_expand_policy,
    tree_stats,
)


# ---------------------------------------------------------------------------
# Helpers: fake traversal objects
# ---------------------------------------------------------------------------

def _node(uid, depth, cumulative, direct, supply=1.0, activity_id=None):
    return SimpleNamespace(
        unique_id=uid,
        depth=depth,
        cumulative_score=cumulative,
        direct_emissions_score=direct,
        supply_amount=supply,
        activity_datapackage_id=activity_id or uid,
    )


def _edge(consumer_uid, producer_uid):
    return SimpleNamespace(
        consumer_unique_id=consumer_uid,
        producer_unique_id=producer_uid,
    )


# ---------------------------------------------------------------------------
# build_parent_child_map
# ---------------------------------------------------------------------------

def test_parent_child_map_basic():
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 2.0),
        2: _node(2, 1, 4.0, 1.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    pcm = build_parent_child_map(nodes, edges)
    assert sorted(pcm[-1]) == [1, 2]
    assert pcm[1] == []
    assert pcm[2] == []


def test_parent_child_map_root_no_children():
    nodes = {-1: _node(-1, 0, 5.0, 0.0)}
    edges = []
    pcm = build_parent_child_map(nodes, edges)
    assert pcm[-1] == []


def test_parent_child_map_deep():
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 1.0),
        2: _node(2, 2, 3.0, 1.0),
    }
    edges = [_edge(-1, 1), _edge(1, 2)]
    pcm = build_parent_child_map(nodes, edges)
    assert pcm[-1] == [1]
    assert pcm[1] == [2]
    assert pcm[2] == []


def test_parent_child_map_no_duplicate_children():
    """Duplicate edges should not produce duplicate child entries."""
    nodes = {-1: _node(-1, 0, 10.0, 0.0), 1: _node(1, 1, 6.0, 1.0)}
    edges = [_edge(-1, 1), _edge(-1, 1)]  # duplicate
    pcm = build_parent_child_map(nodes, edges)
    assert pcm[-1].count(1) == 1


# ---------------------------------------------------------------------------
# cumulative_percent / direct_percent
# ---------------------------------------------------------------------------

def test_cumulative_percent_normal():
    node = _node(1, 1, 6.0, 2.0)
    assert cumulative_percent(node, 10.0) == pytest.approx(60.0)


def test_cumulative_percent_zero_total():
    node = _node(1, 1, 6.0, 2.0)
    assert cumulative_percent(node, 0.0) == 0.0


def test_cumulative_percent_full():
    node = _node(1, 1, 10.0, 5.0)
    assert cumulative_percent(node, 10.0) == pytest.approx(100.0)


def test_direct_percent_normal():
    node = _node(1, 1, 6.0, 2.0)
    assert direct_percent(node, 10.0) == pytest.approx(20.0)


def test_direct_percent_zero_total():
    node = _node(1, 1, 6.0, 2.0)
    assert direct_percent(node, 0.0) == 0.0


# ---------------------------------------------------------------------------
# build_sunburst_rings
# ---------------------------------------------------------------------------

def _simple_tree():
    """Two-tier tree: root → A(6), B(4); A → C(3), D(2)."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 1.0),
        2: _node(2, 1, 4.0, 1.0),
        3: _node(3, 2, 3.0, 1.0),
        4: _node(4, 2, 2.0, 1.0),
    }
    edges = [
        _edge(-1, 1), _edge(-1, 2),
        _edge(1, 3), _edge(1, 4),
    ]
    return nodes, edges


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
    assert len(rings) == 1  # only tier-1 ring


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


# ---------------------------------------------------------------------------
# build_chain_layout
# ---------------------------------------------------------------------------

def _rf_supplier_tree():
    """Virtual root → RF (uid 0) → suppliers; parent uid 0 must not be falsy."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 3.0, activity_id=100),
        1: _node(1, 2, 6.0, 1.0, activity_id=101),
        2: _node(2, 2, 3.0, 1.0, activity_id=102),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(0, 2)]
    return nodes, edges


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


def test_is_terminal_node():
    nodes, edges = _rf_supplier_tree()
    visited = {0, 1, 2}
    assert is_terminal_node(nodes, edges, visited, 1) is True
    assert is_terminal_node(nodes, edges, visited, 0) is False
    assert is_terminal_node(nodes, edges, {0}, 1) is False


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


def test_direct_impact_intensity_log_scale():
    lo = direct_impact_intensity(1.0, 100.0)
    mid = direct_impact_intensity(10.0, 100.0)
    hi = direct_impact_intensity(100.0, 100.0)
    assert lo == pytest.approx(0.0)
    assert hi == pytest.approx(1.0)
    assert mid == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# flatten_to_dataframe
# ---------------------------------------------------------------------------

def _meta(uid):
    return {
        "product": f"product_{uid}",
        "name": f"process_{uid}",
        "location": "GLO",
        "database": "testdb",
        "unit": "kg",
    }


def test_flatten_to_dataframe_row_count():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=_meta)
    # Virtual root skipped; 4 visible nodes
    assert len(df) == 4


def test_flatten_to_dataframe_no_duplicates():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=_meta)
    assert df.duplicated().sum() == 0


def test_flatten_to_dataframe_tier_column():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=_meta)
    # RF = 0, their suppliers = 1
    assert set(df["Tier"].tolist()) == {0, 1}


def test_flatten_to_dataframe_root_cumulative_percent():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=_meta)
    t0 = df[df["Tier"] == 0]
    assert t0["Cumulative impact (%)"].sum() == pytest.approx(100.0)


def test_flatten_to_dataframe_columns():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0)
    expected = [
        "Cumulative impact (%)", "Direct impact (%)", "Product", "Process",
        "Location", "Database", "Flow amount", "Unit", "Cumulative impact",
        "Direct impact", "Tier",
    ]
    assert list(df.columns) == expected


def test_flatten_to_dataframe_depth_first_order():
    """Root → node1 → node3 → node4 → node2 in DFS."""
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=_meta)
    # Node 3 and 4 (children of 1) should appear before node 2 (sibling of 1)
    idx_1 = df.index[df["Cumulative impact"] == 6.0].tolist()[0]
    idx_2 = df.index[df["Cumulative impact"] == 4.0].tolist()[0]
    idx_3 = df.index[df["Cumulative impact"] == 3.0].tolist()[0]
    assert idx_1 < idx_3 < idx_2


def test_flatten_to_dataframe_no_metadata_lookup():
    nodes, edges = _simple_tree()
    df = flatten_to_dataframe(nodes, edges, 10.0, metadata_lookup=None)
    assert (df["Product"] == "").all()
    assert (df["Process"] == "").all()


# ---------------------------------------------------------------------------
# direct_impact_coverage / tree_stats / next_expand_candidates
# ---------------------------------------------------------------------------

def _visible_nodes():
    """Depth-0 virtual root + three tier-1 suppliers (no further children yet)."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 50.0, 20.0),
        2: _node(2, 1, 30.0, 10.0),
        3: _node(3, 1, 20.0, 5.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(-1, 3)]
    return nodes, edges


def test_direct_impact_coverage_partial():
    nodes, _ = _visible_nodes()
    # With root_uid: skip virtual root; 20+10+5 = 35 / 100
    assert direct_impact_coverage(nodes, 100.0, root_uid=-1) == pytest.approx(0.35)
    # Without root_uid: depth must not be used as a filter (root direct is 0)
    assert direct_impact_coverage(nodes, 100.0) == pytest.approx(0.35)


def test_direct_impact_coverage_ignores_mutated_depth():
    """After traverse_from_node we zero depth; coverage must still count nodes."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 0, 50.0, 20.0),
        2: _node(2, 0, 30.0, 15.0),
    }
    assert direct_impact_coverage(nodes, 100.0, root_uid=-1) == pytest.approx(0.35)


def test_direct_impact_coverage_zero_total():
    nodes, _ = _visible_nodes()
    assert direct_impact_coverage(nodes, 0.0) == 0.0


def test_direct_impact_coverage_empty():
    assert direct_impact_coverage({}, 100.0) == 0.0


def test_tree_stats():
    nodes, edges = _visible_nodes()
    stats = tree_stats(nodes, 100.0, root_uid=-1, edges=edges)
    assert stats["node_count"] == 3
    assert stats["coverage"] == pytest.approx(0.35)
    assert stats["max_tier"] == 0  # RF rows at display tier 0


def test_tree_stats_max_tier_ignores_mutated_depth():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 0, 50.0, 10.0),   # mutated
        11: _node(11, 0, 20.0, 5.0),  # mutated
    }
    edges = [_edge(-1, 1), _edge(1, 11)]
    stats = tree_stats(nodes, 100.0, root_uid=-1, edges=edges)
    assert stats["max_tier"] == 1


def test_tier_candidates_expand_depth_below_n():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 60.0, 10.0),
        2: _node(2, 1, 40.0, 10.0),
        11: _node(11, 2, 30.0, 5.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(1, 11)]
    visited = {-1, 1}  # 2 and 11 not visited
    cands = next_expand_candidates(
        nodes, edges, visited, mode="tier", value=3, total_score=100.0, root_uid=-1
    )
    # Display tiers: 1→0, 2→0, 11→1; unvisited with tier < 3
    assert set(cands) == {2, 11}


def test_compute_node_tiers_ignores_mutated_depth():
    from activity_browser.bwutils.contribution_tree import compute_node_tiers

    # After traverse_from_node, Brightway may reset a mid-tree node's depth to 0
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 0, 50.0, 10.0),   # mutated depth!
        11: _node(11, 1, 20.0, 5.0),  # mutated child depth
    }
    edges = [_edge(-1, 1), _edge(1, 11)]
    tiers = compute_node_tiers(nodes, edges, root_uid=-1)
    assert -1 not in tiers
    assert tiers[1] == 0
    assert tiers[11] == 1


def test_path_candidates_above_threshold_only():
    nodes, edges = _visible_nodes()
    visited = {-1}  # none of the RF nodes visited
    cands = next_expand_candidates(
        nodes, edges, visited, mode="path", value=35.0, total_score=100.0
    )
    # Only node 1 has cumulative 50 >= 35% of total
    assert cands == [1]


def test_path_skips_already_visited():
    nodes, edges = _visible_nodes()
    visited = {-1, 1}
    cands = next_expand_candidates(
        nodes, edges, visited, mode="path", value=1.0, total_score=100.0
    )
    assert set(cands) == {2, 3}


def test_path_does_not_auto_expand_children_below_threshold():
    """Sub-threshold path-impact children stay out of the candidate set."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 50.0, 10.0),
        11: _node(11, 2, 40.0, 5.0),   # 40% path — above 10%
        12: _node(12, 2, 5.0, 1.0),    # 5% path — below 10%
    }
    edges = [_edge(-1, 1), _edge(1, 11), _edge(1, 12)]
    visited = {-1, 1}  # parent already expanded; children present but unvisited
    cands = next_expand_candidates(
        nodes, edges, visited, mode="path", value=10.0, total_score=100.0
    )
    assert cands == [11]
    assert 12 not in cands


def test_next_expand_candidates_rejects_cumulative_mode():
    """Cumulative expand must use plan_cumulative_expand, not this helper."""
    nodes, edges = _visible_nodes()
    with pytest.raises(ValueError, match="plan_cumulative_expand"):
        next_expand_candidates(
            nodes, edges, {-1}, mode="cumulative", value=50.0, total_score=100.0
        )


def test_plan_cumulative_stops_near_target_not_all_nodes():
    """Deep calculated graph: display set should stay near the target, not dump all."""
    # RF --20--> A --40--> B --30--> C (directs). Extra deep branch D,E unused for 50%.
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 90.0, 5.0),   # RF
        2: _node(2, 2, 80.0, 10.0),  # A
        3: _node(3, 3, 60.0, 40.0),  # B — opening A then B should cross 50%
        4: _node(4, 4, 20.0, 20.0),  # C
        5: _node(5, 2, 5.0, 5.0),    # sibling noise under RF
        6: _node(6, 3, 4.0, 4.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 5),
        _edge(2, 3),
        _edge(3, 4),
        _edge(5, 6),
    ]
    visited = set(nodes)  # everything already calculated
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 50.0, visited
    )
    assert need is None
    # Must not pull in the whole graph (4, 6 especially)
    assert 4 not in included
    assert 6 not in included
    assert coverage_of_uids(nodes, included, 100.0) >= 0.50
    assert coverage_of_uids(nodes, included, 100.0) < 0.80
    assert 1 in to_expand  # opened RF path


def test_plan_cumulative_adds_only_needed_siblings():
    """Last open must not dump every sibling once the target is already met."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 10.0),  # RF
        # Children of RF: largest cumulative first; directs 25 each after RF's 10
        2: _node(2, 2, 50.0, 25.0),
        3: _node(3, 2, 40.0, 25.0),
        4: _node(4, 2, 30.0, 25.0),
        5: _node(5, 2, 20.0, 25.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 3),
        _edge(1, 4),
        _edge(1, 5),
    ]
    visited = set(nodes)
    # Target 60%: RF(10) + child2(25) + child3(25) = 60 — must NOT add 4 and 5
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 60.0, visited
    )
    assert need is None
    assert to_expand == {1}
    assert included == {1, 2, 3}
    assert coverage_of_uids(nodes, included, 100.0) == pytest.approx(0.60)


def test_plan_cumulative_skips_mostly_direct_terminal():
    """Peat-moss-like node: high direct, tiny upstream — listed but not opened."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 20.0),   # RF
        2: _node(2, 2, 50.0, 5.0),     # continue path (lots of upstream)
        3: _node(3, 3, 40.0, 39.0),    # ~97.5% direct — must NOT open
        4: _node(4, 4, 0.5, 0.3),
        5: _node(5, 4, 0.3, 0.2),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(2, 3),
        _edge(3, 4),
        _edge(3, 5),
    ]
    visited = set(nodes)
    # 20 + 5 + 39 = 64% once node 3 is listed under opened node 2
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 60.0, visited
    )
    assert need is None
    assert coverage_of_uids(nodes, included, 100.0) >= 0.60
    assert 3 in included
    assert 3 not in to_expand
    assert 4 not in included and 5 not in included
    assert 1 in to_expand and 2 in to_expand


def test_plan_cumulative_requests_traverse_for_unvisited():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 90.0, 5.0),
    }
    edges = [_edge(-1, 1)]
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 60.0, visited={-1}
    )
    assert need == 1
    assert included == {1}
    assert to_expand == set()


def test_coverage_of_uids():
    nodes = {
        1: _node(1, 1, 50.0, 20.0),
        2: _node(2, 1, 30.0, 10.0),
    }
    assert coverage_of_uids(nodes, {1, 2}, 100.0) == pytest.approx(0.30)
    assert coverage_of_uids(nodes, {1}, 100.0) == pytest.approx(0.20)


def test_path_display_set_keeps_below_threshold_siblings():
    """Path expand opens nodes that continue a >=X% path; lists their siblings."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 5.0),   # RF — above 10%, has child 2 >= 10% → expand
        2: _node(2, 2, 40.0, 10.0),   # above 10%, has child 4 >= 10% → expand
        3: _node(3, 2, 5.0, 1.0),     # below 10% sibling — listed under expanded RF
        4: _node(4, 3, 30.0, 8.0),    # above 10%, no child >= 10% → listed, NOT expanded
        5: _node(5, 3, 2.0, 0.5),     # below 10% sibling under 2 — listed
        6: _node(6, 3, 1.0, 0.2),     # child of 3 — not listed (3 not expanded)
        7: _node(7, 4, 1.0, 0.1),     # child of terminal 4 — must NOT be listed
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 3),
        _edge(2, 4),
        _edge(2, 5),
        _edge(3, 6),
        _edge(4, 7),
    ]
    visited = {-1, 1, 2, 4}
    included, to_expand = path_display_set(
        nodes, edges, -1, 100.0, 10.0, visited
    )
    assert 3 in included  # sibling under RF
    assert 5 in included  # sibling under node 2
    assert 4 in included  # terminal high-path node stays visible
    assert 4 not in to_expand  # but is not auto-opened
    assert 7 not in included  # children of terminal high-path stay hidden
    assert 6 not in included
    assert to_expand == {1, 2}


def test_path_display_set_terminal_high_path_not_opened():
    """Like peat moss at 12% with only <2% children — show the row, don't open it."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 30.0),
        2: _node(2, 2, 12.5, 12.0),
        3: _node(3, 3, 0.26, 0.1),
        4: _node(4, 3, 0.10, 0.05),
    }
    edges = [_edge(-1, 1), _edge(1, 2), _edge(2, 3), _edge(2, 4)]
    visited = {-1, 1, 2}
    included, to_expand = path_display_set(
        nodes, edges, -1, 100.0, 2.0, visited
    )
    assert 2 in included
    assert 2 not in to_expand
    assert 3 not in included and 4 not in included
    assert to_expand == {1}


# ---------------------------------------------------------------------------
# run_expand_policy — Stop / on_progress False
# ---------------------------------------------------------------------------

class _FakeTraversalState:
    """Minimal stand-in for SameNodeEachVisitGraphTraversal."""

    def __init__(self, nodes, edges, visited):
        self.nodes = nodes
        self.edges = list(edges)
        self.visited_nodes = set(visited)
        self._root_node = nodes[-1]
        self.traversed: list[int] = []

    def traverse_from_node(self, unique_id, depth=1):
        self.traversed.append(unique_id)
        self.visited_nodes.add(unique_id)
        return True


def _expand_chain_state(*, visited=None):
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 90.0, 5.0),
        2: _node(2, 2, 80.0, 10.0),
        3: _node(3, 3, 60.0, 40.0),
    }
    edges = [_edge(-1, 1), _edge(1, 2), _edge(2, 3)]
    return _FakeTraversalState(nodes, edges, visited or {-1})


def test_run_expand_policy_stops_when_on_progress_returns_false():
    """on_progress False keeps the current graph; omit it to traverse as before."""
    stopped = _expand_chain_state()
    run_expand_policy(
        stopped,
        mode="cumulative",
        value=60.0,
        total_score=100.0,
        on_progress=lambda step, n: False,
    )
    assert stopped.traversed == []

    finished = _expand_chain_state()
    run_expand_policy(finished, mode="cumulative", value=60.0, total_score=100.0)
    assert 1 in finished.traversed
    assert 2 in finished.traversed


def test_activity_metadata_for_ids_from_metadatastore_frame():
    df = pd.DataFrame(
        {
            "id": pd.array([10, 20], dtype="Int64"),
            "name": ["Steel production", "Aluminium production"],
            "product": ["steel", None],
            "location": ["RER", "GLO"],
            "database": ["db", "db"],
            "unit": ["kg", "kg"],
        }
    )
    assert activity_metadata_for_ids([]) == {}
    out = activity_metadata_for_ids([10, 20, 99], df)
    assert out[10]["product"] == "steel"
    assert out[10]["name"] == "Steel production"
    assert out[20]["product"] == "Aluminium production"
    assert 99 not in out
