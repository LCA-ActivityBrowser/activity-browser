"""Unique-process Sankey helpers (no Qt)."""

from __future__ import annotations

import pytest

from activity_browser.bwutils.graph_traversal.engine import coverage_of_uids
from activity_browser.bwutils.graph_traversal.sankey import (
    apply_graph_display_click,
    graph_display_set,
    include_new_unique_suppliers,
    keep_best_visit_per_activity,
    run_expand_policy,
    sankey_traversal_max_depth,
    toggle_graph_display_node,
    unique_process_stats,
    unopened_same_activity_hops,
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


def test_sankey_traversal_max_depth_tier_includes_cycle_hop():
    assert sankey_traversal_max_depth("tier", 1) == 3
    assert sankey_traversal_max_depth("tier", 0) == 2
    assert sankey_traversal_max_depth(None, 1) == 3
    assert sankey_traversal_max_depth("path", 1.0) is None
    assert sankey_traversal_max_depth("cumulative", 50) is None


def test_keep_best_visit_per_activity_drops_unrolled_cycle():
    nodes, edges = _circular_ab_visits()
    kept = keep_best_visit_per_activity(nodes, edges, {0, 1, 2}, root_uid=-1)
    assert kept == {0, 1}


def test_keep_best_visit_prefers_larger_path_not_bfs_first():
    """Two RF connections to the same process: keep the 36% visit, not the 0.5% one."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 0.5, 0.1, activity_id=10),
        2: _node(2, 1, 36.0, 0.17, activity_id=10),
        3: _node(3, 2, 30.0, 1.0, activity_id=20),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(2, 3)]
    kept = keep_best_visit_per_activity(nodes, edges, {1, 2, 3}, root_uid=-1)
    assert kept == {2, 3}


def test_graph_display_set_path_unique_follows_large_path():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 0.5, 0.1, activity_id=10),
        2: _node(2, 1, 36.0, 0.17, activity_id=10),
        3: _node(3, 2, 30.0, 1.0, activity_id=20),
    }
    edges = [_edge(-1, 1), _edge(-1, 2), _edge(2, 3)]
    included, to_expand = graph_display_set(
        nodes,
        edges,
        mode="path",
        value=0.3,
        total_score=100.0,
        root_uid=-1,
        visited={-1, 1, 2, 3},
    )
    assert 2 in included
    assert 1 not in included
    assert 3 in included
    assert 2 in to_expand


def test_graph_display_set_cumulative_unique_ignores_later_visits():
    """Sankey must not use a later NNEV visit of the same process to hit the target.

    Without unique-first planning, the later visit's direct would cross 20%, then
    collapsing to first-visit would drop that coverage.
    """
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        0: _node(0, 1, 100.0, 10.0, activity_id=10),
        1: _node(1, 2, 50.0, 2.0, activity_id=11),
        2: _node(2, 3, 40.0, 15.0, activity_id=11),
        3: _node(3, 2, 20.0, 12.0, activity_id=12),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(1, 2), _edge(0, 3)]
    included, _to_expand = graph_display_set(
        nodes,
        edges,
        mode="cumulative",
        value=20.0,
        total_score=100.0,
        root_uid=-1,
        visited=set(nodes),
    )
    assert 2 not in included
    assert 3 in included
    assert coverage_of_uids(nodes, included, 100.0) >= 0.20


def test_graph_display_set_unique_activities_keeps_two_cycle_processes():
    nodes, edges = _circular_ab_visits()
    included, _to_expand = graph_display_set(
        nodes,
        edges,
        mode="tier",
        value=5,
        total_score=10.0,
        root_uid=-1,
        visited=set(nodes),
    )
    assert included == {0, 1}


def test_toggle_unique_activities_does_not_unroll_cycle():
    nodes, edges = _circular_ab_visits()
    included = {0, 1}
    clicked = toggle_graph_display_node(included, nodes, edges, 1)
    assert clicked == {0, 1}



def test_run_expand_policy_unique_does_not_traverse_later_cycle_visit():
    nodes, edges = _circular_ab_visits()
    state = _FakeTraversalState(nodes, edges, visited={-1, 0, 1})
    included, _to_expand = run_expand_policy(
        state,
        mode="cumulative",
        value=50.0,
        total_score=10.0,
    )
    assert 2 not in state.traversed
    assert 2 not in (included or set())


def test_run_expand_policy_path_unique_hops_highest_path_visit():
    """Small first visit of P must not block hopping the 36% visit of P."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 0.5, 0.1, activity_id=10),
        2: _node(2, 1, 36.0, 0.17, activity_id=10),
    }
    edges = [_edge(-1, 1), _edge(-1, 2)]
    state = _FakeTraversalState(nodes, edges, visited={-1})
    run_expand_policy(
        state,
        mode="path",
        value=0.3,
        total_score=100.0,
    )
    assert 2 in state.traversed
    assert 1 not in state.traversed


def test_unique_process_stats_counts_first_visits_not_later_cycle():
    nodes, edges = _circular_ab_visits()
    stats = unique_process_stats(nodes, edges, -1, 10.0, included={0, 1})
    assert stats["shown_n"] == 2
    assert stats["calc_n"] == 2


def test_toggle_unique_expands_hidden_siblings_before_collapse():
    """Manual expand shows every calculated supplier; collapse only when all are shown."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 1.0, activity_id=100),
        1: _node(1, 2, 8.0, 0.0, activity_id=101),
        3: _node(3, 2, 0.5, 0.5, activity_id=103),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(0, 3)]
    expanded = toggle_graph_display_node(
        {0, 1}, nodes, edges, 0, root_uid=-1
    )
    assert expanded == {0, 1, 3}
    collapsed = toggle_graph_display_node(
        expanded, nodes, edges, 0, root_uid=-1
    )
    assert collapsed == {0}


def test_toggle_unique_activities_still_adds_new_process():
    nodes, edges = _circular_ab_visits()
    nodes[3] = _node(3, 3, 1.0, 1.0, activity_id=103)
    edges = list(edges) + [_edge(1, 3)]
    expanded = toggle_graph_display_node(
        {0, 1}, nodes, edges, 1
    )
    assert expanded == {0, 1, 3}


def test_toggle_unique_collapse_keeps_ancestor_cycle_partner():
    """Hide exclusive suppliers; keep a circular-supply ancestor on the RF path."""
    nodes = {
        -1: _node(-1, 0, 10.0, 0.0),
        0: _node(0, 1, 10.0, 1.0, activity_id=100),
        1: _node(1, 2, 8.0, 0.0, activity_id=101),
        3: _node(3, 3, 1.0, 1.0, activity_id=103),
    }
    edges = [_edge(-1, 0), _edge(0, 1), _edge(1, 0), _edge(1, 3)]
    collapsed = toggle_graph_display_node(
        {0, 1, 3}, nodes, edges, 1, root_uid=-1
    )
    assert collapsed == {0, 1}


def test_apply_graph_display_click_requests_hop_when_unopened():
    nodes, edges = _circular_ab_visits()
    included, hop = apply_graph_display_click(
        {0, 1},
        nodes,
        edges,
        1,
        opened={0},
        root_uid=-1,
    )
    assert hop == 1
    assert included == {0, 1}


def test_include_new_unique_suppliers_after_hop():
    nodes, edges = _circular_ab_visits()
    nodes[3] = _node(3, 3, 1.0, 1.0, activity_id=103)
    edges = list(edges) + [_edge(1, 3)]
    shown = include_new_unique_suppliers({0, 1}, nodes, edges, 1, root_uid=-1)
    assert shown == {0, 1, 3}


def test_toggle_unique_adds_suppliers_from_other_visit():
    """Click the large-path box; suppliers of the small visit still join the display set."""
    nodes, edges = _two_visits_different_suppliers()
    expanded = toggle_graph_display_node(
        {2, 4}, nodes, edges, 2, root_uid=-1
    )
    assert 3 in expanded
    assert 4 in expanded


def test_include_new_unique_suppliers_unions_other_visits():
    nodes, edges = _two_visits_different_suppliers()
    shown = include_new_unique_suppliers({2}, nodes, edges, 2, root_uid=-1)
    assert shown == {2, 3, 4}


def test_apply_click_hops_other_unopened_visit_of_same_process():
    """Displayed visit is already opened; the other visit of P still needs a hop."""
    nodes, edges = _two_visits_different_suppliers()
    included, hop = apply_graph_display_click(
        {2},
        nodes,
        edges,
        2,
        opened={-1, 2},
        root_uid=-1,
    )
    assert hop == 1
    assert included == {2}
    assert unopened_same_activity_hops(nodes, 2, {-1, 2}) == [1]
