"""Visit-based graph-traversal engine helpers (no Qt)."""

from __future__ import annotations

import pandas as pd
import pytest

from activity_browser.bwutils.graph_traversal.engine import (
    activity_metadata_for_ids,
    build_parent_child_map,
    compute_node_tiers,
    coverage_of_uids,
    cumulative_percent,
    direct_impact_coverage,
    direct_percent,
    graph_display_set,
    is_terminal_node,
    next_expand_candidates,
    path_display_set,
    plan_cumulative_expand,
    run_expand_policy,
    toggle_graph_display_node,
)

from graph_traversal_fakes import (
    _FakeTraversalState,
    _circular_ab_visits,
    _edge,
    _expand_chain_state,
    _node,
    _rf_supplier_tree,
    _simple_tree,
    _two_visits_different_suppliers,
    _visible_nodes,
)


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


def test_is_terminal_node():
    nodes, edges = _rf_supplier_tree()
    visited = {0, 1, 2}
    assert is_terminal_node(nodes, edges, visited, 1) is True
    assert is_terminal_node(nodes, edges, visited, 0) is False
    assert is_terminal_node(nodes, edges, {0}, 1) is False


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
    assert 1 in to_expand


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


def test_plan_cumulative_lists_mostly_direct_without_opening_when_target_met():
    """Once coverage is met, leftover children of a mostly-direct node stay out."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 20.0),
        2: _node(2, 2, 50.0, 5.0),
        3: _node(3, 3, 40.0, 39.0),
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
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 60.0, visited
    )
    assert need is None
    assert coverage_of_uids(nodes, included, 100.0) >= 0.60
    assert 3 in included
    assert 3 not in to_expand
    assert 4 not in included and 5 not in included
    assert 1 in to_expand and 2 in to_expand


def test_plan_cumulative_opens_mostly_direct_when_children_needed_for_target():
    """No 5% skip: open a mostly-direct node if its children are still needed."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 10.0),
        2: _node(2, 2, 90.0, 5.0),
        3: _node(3, 3, 80.0, 77.0),
        4: _node(4, 4, 2.0, 2.0),
        5: _node(5, 4, 1.0, 1.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(2, 3),
        _edge(3, 4),
        _edge(3, 5),
    ]
    visited = set(nodes)
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 95.0, visited
    )
    assert need is None
    assert coverage_of_uids(nodes, included, 100.0) >= 0.95
    assert 3 in to_expand
    assert 4 in included
    assert 5 in included


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


def test_plan_cumulative_inventory_directs_stop_without_dumping_zero_direct_siblings():
    """Unique-process coverage uses inventory directs so 0-visit-direct plants count."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 0.0, activity_id=10),
        2: _node(2, 2, 25.0, 0.0, activity_id=20),
        3: _node(3, 2, 20.0, 0.0, activity_id=30),
        4: _node(4, 2, 15.0, 0.0, activity_id=40),
        5: _node(5, 2, 10.0, 0.0, activity_id=50),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 3),
        _edge(1, 4),
        _edge(1, 5),
    ]
    visited = set(nodes)
    inv = {1: 0.0, 2: 25.0, 3: 0.0, 4: 0.0, 5: 0.0}

    def lookup(uid):
        return inv.get(uid, 0.0)

    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 20.0, visited, direct_lookup=lookup
    )
    assert need is None
    assert 2 in included
    assert 3 not in included
    assert 4 not in included
    assert 5 not in included
    assert coverage_of_uids(
        nodes, included, 100.0, direct_lookup=lookup
    ) >= 0.20
    # Visit-level directs stay 0 — without the lookup this would dump every sibling
    assert coverage_of_uids(nodes, included, 100.0) == pytest.approx(0.0)


def test_plan_cumulative_hides_zero_direct_siblings_not_on_opened_path():
    """0-direct markets must not enter the display set while coverage is stuck.

    Individual path hides siblings below the path threshold. Cumulative must
    not list every 0-direct sibling of an opened node — only the next
    remaining-upstream hop and children that raise coverage.
    """
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 0.0),  # RF
        2: _node(2, 2, 80.0, 0.0),  # market on the large path
        3: _node(3, 3, 25.0, 25.0),  # plant under 2
        4: _node(4, 2, 10.0, 0.0),  # sibling market — not needed for 20%
        5: _node(5, 2, 5.0, 0.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 4),
        _edge(1, 5),
        _edge(2, 3),
    ]
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 20.0, set(nodes)
    )
    assert need is None
    assert 2 in included and 3 in included
    assert 1 in to_expand and 2 in to_expand
    assert 4 not in included
    assert 5 not in included
    assert coverage_of_uids(nodes, included, 100.0) >= 0.20


def test_plan_cumulative_opens_next_zero_direct_sibling_when_coverage_still_short():
    """After the first 0-direct hop, leftover siblings can still be opened if needed."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 0.0),
        2: _node(2, 2, 50.0, 0.0),
        3: _node(3, 3, 40.0, 40.0),
        4: _node(4, 2, 40.0, 0.0),
        5: _node(5, 3, 40.0, 40.0),
        6: _node(6, 2, 5.0, 0.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(1, 4),
        _edge(1, 6),
        _edge(2, 3),
        _edge(4, 5),
    ]
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 75.0, set(nodes)
    )
    assert need is None
    assert 2 in included and 3 in included
    assert 4 in included and 5 in included
    assert 6 not in included
    assert coverage_of_uids(nodes, included, 100.0) >= 0.75


def test_plan_cumulative_hides_zero_direct_markets_beside_direct_plants():
    """Silicon / alumina markets stay hidden next to plants that already add direct.

    Follow the plant's remaining upstream (electricity) instead of listing every
    leftover 0-direct sibling of that plant.
    """
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 0.0),
        2: _node(2, 2, 90.0, 0.0),
        3: _node(3, 3, 80.0, 8.5),
        4: _node(4, 3, 0.4, 0.0),
        5: _node(5, 4, 36.0, 0.0),
        6: _node(6, 4, 1.0, 0.0),
        7: _node(7, 4, 0.5, 0.3),
        8: _node(8, 5, 30.0, 30.0),
    }
    edges = [
        _edge(-1, 1),
        _edge(1, 2),
        _edge(2, 3),
        _edge(2, 4),
        _edge(3, 5),
        _edge(3, 6),
        _edge(3, 7),
        _edge(5, 8),
    ]
    included, to_expand, need = plan_cumulative_expand(
        nodes, edges, -1, 100.0, 20.0, set(nodes)
    )
    assert need is None
    assert 3 in included and 8 in included
    assert 5 in included
    assert 4 not in included
    assert 6 not in included
    assert coverage_of_uids(nodes, included, 100.0) >= 0.20


def test_path_display_set_hides_below_threshold_siblings():
    """Path expand opens nodes that continue a >=X% path; hides below-threshold siblings."""
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 1, 100.0, 5.0),   # RF — above 10%, has child 2 >= 10% → expand
        2: _node(2, 2, 40.0, 10.0),   # above 10%, has child 4 >= 10% → expand
        3: _node(3, 2, 5.0, 1.0),     # below 10% sibling — hidden
        4: _node(4, 3, 30.0, 8.0),    # above 10%, no child >= 10% → listed, NOT expanded
        5: _node(5, 3, 2.0, 0.5),     # below 10% sibling under 2 — hidden
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
    assert 3 not in included  # sibling under RF
    assert 5 not in included  # sibling under node 2
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
    assert out[10]["code"] == ""
    assert out[20]["product"] == "Aluminium production"
    assert 99 not in out


def test_activity_metadata_for_ids_includes_code_from_index():
    df = pd.DataFrame(
        {
            "id": pd.array([10], dtype="Int64"),
            "name": ["Steel production"],
            "product": ["steel"],
            "location": ["RER"],
            "database": ["db"],
            "unit": ["kg"],
            "key": [("db", "steel-code")],
        }
    )
    df.index = pd.MultiIndex.from_tuples([("db", "steel-code")], names=["database", "code"])
    out = activity_metadata_for_ids([10], df)
    assert out[10]["code"] == "steel-code"
    assert out[10]["database"] == "db"


def test_graph_display_set_tier_zero_is_reference_flow_only():
    nodes, edges = _rf_supplier_tree()
    included, to_expand = graph_display_set(
        nodes,
        edges,
        mode="tier",
        value=0,
        total_score=10.0,
        root_uid=-1,
        visited=set(nodes),
    )
    assert included == {0}
    assert to_expand == set()


def test_graph_display_set_tier_one_includes_suppliers():
    nodes, edges = _rf_supplier_tree()
    included, to_expand = graph_display_set(
        nodes,
        edges,
        mode="tier",
        value=1,
        total_score=10.0,
        root_uid=-1,
        visited=set(nodes),
    )
    assert included == {0, 1, 2}
    assert 0 in to_expand


def test_toggle_graph_display_collapses_and_expands_children():
    nodes, edges = _rf_supplier_tree()
    included = {0, 1, 2}
    collapsed = toggle_graph_display_node(included, nodes, edges, 0)
    assert collapsed == {0}
    expanded = toggle_graph_display_node(collapsed, nodes, edges, 0)
    assert expanded == {0, 1, 2}


def test_toggle_visit_unrolls_cycle():
    nodes, edges = _circular_ab_visits()
    included = {0, 1}
    unrolled = toggle_graph_display_node(included, nodes, edges, 1)
    assert unrolled == {0, 1, 2}


def test_old_contribution_tree_module_removed():
    with pytest.raises(ModuleNotFoundError):
        import activity_browser.bwutils.contribution_tree  # noqa: F401

