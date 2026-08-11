"""Tests for bwutils.contribution_tree data helpers.

All tests use plain SimpleNamespace fake objects — no Qt, no Brightway project.
Pattern follows tests/test_contribution_normalize.py and test_lcia_overview.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from activity_browser.bwutils.contribution_tree import (
    build_parent_child_map,
    build_sunburst_rings,
    coverage_of_uids,
    cumulative_percent,
    direct_impact_coverage,
    direct_percent,
    flatten_to_dataframe,
    next_expand_candidates,
    path_display_set,
    plan_cumulative_expand,
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
    real_wedges = [w for w in ring if not w["is_other"]]
    shares = {w["unique_id"]: w["share"] for w in real_wedges}
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


def test_sunburst_rings_other_wedge_present_when_children_dont_sum():
    """Children C(3) + D(2) = 5; parent A(6) → other = 1/6."""
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=2)
    ring2 = rings[1]
    others = [w for w in ring2 if w["is_other"] and w["parent_unique_id"] == 1]
    assert len(others) == 1
    assert others[0]["share"] == pytest.approx(1 / 6, rel=1e-6)


def test_sunburst_rings_max_depth_respected():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=1)
    assert len(rings) == 1  # only tier-1 ring


def test_sunburst_rings_empty_on_zero_total():
    nodes, edges = _simple_tree()
    rings = build_sunburst_rings(nodes, edges, 0.0, max_depth=2)
    assert rings == []


def test_sunburst_rings_no_other_when_children_match_parent():
    """When children sum exactly to parent, no 'other' wedge for that parent."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        1: _node(1, 1, 6.0, 1.0),
        2: _node(2, 1, 4.0, 1.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    rings = build_sunburst_rings(nodes, edges, 10.0, max_depth=1)
    others = [w for w in rings[0] if w["is_other"]]
    assert others == []


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


def test_cumulative_skips_excluded_and_prefers_eligible():
    """Largest global unvisited is skipped if excluded / not eligible (not in view)."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 80.0, 1.0),   # largest, but not eligible
        2: _node(2, 1, 50.0, 1.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    cands = next_expand_candidates(
        nodes,
        edges,
        {-1},
        mode="cumulative",
        value=90.0,
        total_score=100.0,
        eligible_ids={2},
    )
    assert cands == [2]
    cands2 = next_expand_candidates(
        nodes,
        edges,
        {-1},
        mode="cumulative",
        value=90.0,
        total_score=100.0,
        exclude={1},
    )
    assert cands2 == [2]


def test_cumulative_tie_break_prefers_lower_unique_id():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        5: _node(5, 1, 40.0, 1.0),
        2: _node(2, 1, 40.0, 1.0),
    }
    edges = [_edge(-1, 5), _edge(-1, 2)]
    cands = next_expand_candidates(
        nodes, edges, {-1}, mode="cumulative", value=50.0, total_score=100.0
    )
    assert cands == [2]


def test_cumulative_returns_largest_unvisited_until_coverage():
    nodes, edges = _visible_nodes()
    visited = {-1}
    # coverage of visible directs = 0.35; target 50% → need to expand
    cands = next_expand_candidates(
        nodes, edges, visited, mode="cumulative", value=50.0, total_score=100.0
    )
    # One step: largest unvisited by abs cumulative = node 1 (50)
    assert cands == [1]


def test_cumulative_stops_when_coverage_met():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 50.0, 80.0),
        2: _node(2, 1, 30.0, 10.0),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    visited = {-1}
    cands = next_expand_candidates(
        nodes, edges, visited, mode="cumulative", value=80.0, total_score=100.0
    )
    # visible directs already 90 >= 80%
    assert cands == []


def test_cumulative_empty_when_nothing_left():
    nodes, edges = _visible_nodes()
    visited = set(nodes)
    cands = next_expand_candidates(
        nodes, edges, visited, mode="cumulative", value=99.0, total_score=100.0
    )
    assert cands == []


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
