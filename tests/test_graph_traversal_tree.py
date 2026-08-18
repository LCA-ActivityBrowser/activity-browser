"""Contribution-tree table flatten, stats, and intensity (no Qt)."""

from __future__ import annotations

import pytest

from activity_browser.bwutils.graph_traversal.tree import (
    direct_impact_intensity,
    flatten_to_dataframe,
    tree_stats,
)

from graph_traversal_fakes import (
    _edge,
    _meta,
    _node,
    _simple_tree,
    _visible_nodes,
)


def test_direct_impact_intensity_log_scale():
    lo = direct_impact_intensity(1.0, 100.0)
    mid = direct_impact_intensity(10.0, 100.0)
    hi = direct_impact_intensity(100.0, 100.0)
    assert lo == pytest.approx(0.0)
    assert hi == pytest.approx(1.0)
    assert mid == pytest.approx(0.5)


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


def test_tree_stats():
    nodes, edges = _visible_nodes()
    stats = tree_stats(nodes, 100.0, root_uid=-1, edges=edges)
    assert stats["node_count"] == 3
    assert stats["coverage"] == pytest.approx(0.35)
    assert stats["max_tier"] == 0


def test_tree_stats_max_tier_ignores_mutated_depth():
    nodes = {
        -1: _node(-1, 0, 100.0, 0.0),
        1: _node(1, 0, 50.0, 10.0),   # mutated
        11: _node(11, 0, 20.0, 5.0),  # mutated
    }
    edges = [_edge(-1, 1), _edge(1, 11)]
    stats = tree_stats(nodes, 100.0, root_uid=-1, edges=edges)
    assert stats["max_tier"] == 1
