"""Contribution-tree table helpers (SNEV flatten, footer stats, table colour).

May import ``engine``. Must not import ``sankey``.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from activity_browser.bwutils.graph_traversal.engine import (
    NodeId,
    _visible_contribution_nodes,
    build_parent_child_map,
    compute_node_tiers,
    cumulative_percent,
    direct_impact_coverage,
    direct_percent,
)

def tree_stats(
    nodes: dict,
    total_score: float,
    *,
    root_uid: NodeId | None = None,
    edges: list | None = None,
) -> dict:
    """Return ``node_count``, ``coverage``, and ``max_tier`` for visible nodes.

    ``max_tier`` uses edge-based display tiers when ``root_uid`` and ``edges``
    are provided — never Brightway's mutable ``node.depth``.
    """
    visible = _visible_contribution_nodes(nodes, root_uid)
    if root_uid is not None and edges is not None:
        tiers = compute_node_tiers(nodes, edges, root_uid)
        max_tier = max((tiers.get(n.unique_id, 0) for n in visible), default=0)
    else:
        max_tier = max((getattr(n, "depth", 0) for n in visible), default=0)
    return {
        "node_count": len(visible),
        "coverage": direct_impact_coverage(nodes, total_score, root_uid),
        "max_tier": max_tier,
    }


def direct_impact_intensity(
    value: float,
    column_max: float,
    *,
    floor_ratio: float = 0.01,
) -> float:
    """Map ``|value|`` to ``[0, 1]`` on a log10 axis — same curve as the table delegate."""
    import math

    if column_max <= 0 or value == 0:
        return 0.0
    lo = max(abs(column_max) * floor_ratio, 1e-12)
    hi = abs(column_max)
    if lo >= hi:
        return 1.0 if abs(value) >= hi else 0.0
    v = min(max(abs(value), lo), hi)
    return (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))


def flatten_to_dataframe(
    nodes: dict,
    edges: list,
    total_score: float,
    metadata_lookup: Callable[[int], dict] | None = None,
) -> pd.DataFrame:
    """Depth-first walk of the traversal state; return one row per node.

    Parameters
    ----------
    nodes:
        ``state.nodes`` dict.
    edges:
        ``state.edges`` list.
    total_score:
        ``lca.score``.
    metadata_lookup:
        Optional callable that accepts an ``activity_datapackage_id`` and
        returns a dict with keys ``product``, ``name``, ``location``,
        ``database``, ``unit``.  If None, these columns will be empty strings.
    """
    parent_child = build_parent_child_map(nodes, edges)

    # Find root (depth == 0 or negative unique_id)
    root_candidates = [n for n in nodes.values() if n.depth == 0]
    if not root_candidates:
        return pd.DataFrame()
    root = root_candidates[0]
    tiers = compute_node_tiers(nodes, edges, root.unique_id)

    rows: list[dict] = []
    # Skip virtual demand root — export matches the visible tree (RF = tier 0)
    for child_uid in parent_child.get(root.unique_id, []):
        _dfs(child_uid, nodes, parent_child, total_score, metadata_lookup, rows, tiers)

    return pd.DataFrame(rows, columns=[
        "Cumulative impact (%)",
        "Direct impact (%)",
        "Product",
        "Process",
        "Location",
        "Database",
        "Flow amount",
        "Unit",
        "Cumulative impact",
        "Direct impact",
        "Tier",
    ])


def _dfs(
    uid: NodeId,
    nodes: dict,
    parent_child: dict,
    total_score: float,
    metadata_lookup: Callable | None,
    rows: list,
    tiers: dict[NodeId, int],
) -> None:
    node = nodes.get(uid)
    if node is None:
        return

    meta = {}
    if metadata_lookup is not None:
        meta = metadata_lookup(getattr(node, "activity_datapackage_id", None)) or {}

    rows.append({
        "Cumulative impact (%)": cumulative_percent(node, total_score),
        "Direct impact (%)": direct_percent(node, total_score),
        "Product": meta.get("product", ""),
        "Process": meta.get("name", ""),
        "Location": meta.get("location", ""),
        "Database": meta.get("database", ""),
        "Flow amount": getattr(node, "supply_amount", 0.0),
        "Unit": meta.get("unit", ""),
        "Cumulative impact": getattr(node, "cumulative_score", 0.0),
        "Direct impact": getattr(node, "direct_emissions_score", 0.0),
        "Tier": tiers.get(uid, getattr(node, "depth", 0)),
    })

    for child_uid in parent_child.get(uid, []):
        _dfs(child_uid, nodes, parent_child, total_score, metadata_lookup, rows, tiers)
