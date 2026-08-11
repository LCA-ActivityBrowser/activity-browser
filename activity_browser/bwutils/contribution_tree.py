"""Pure data-preparation helpers for the Contribution Tree tab.

These functions transform a ``SameNodeEachVisitGraphTraversal`` state object
(or any object with compatible ``.nodes`` and ``.edges`` attributes) into the
data structures consumed by the tree item model, the sunburst plot, and the
table export.  No Qt dependency — fully testable with plain fake objects.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable

import pandas as pd

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Type aliases (kept simple to avoid Qt / bw imports at module level)
# ---------------------------------------------------------------------------

NodeId = int  # unique_id of a traversal Node


@contextmanager
def suppress_graph_traversal_warnings():
    """Silence bw_graph_tools coverage ``UserWarning``s (coverage is shown in the UI)."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Graph traversal covered only.*",
            category=UserWarning,
        )
        yield


# ---------------------------------------------------------------------------
# Parent-child map
# ---------------------------------------------------------------------------

def build_parent_child_map(nodes: dict, edges: list) -> dict[NodeId, list[NodeId]]:
    """Return a mapping of parent unique_id → list of child unique_ids.

    The functional-unit root node (unique_id < 0 by convention) is included as
    a key even when it has no children.

    Parameters
    ----------
    nodes:
        ``state.nodes`` dict — keys are ``unique_id`` integers.
    edges:
        ``state.edges`` list — each edge has ``.consumer_unique_id`` (parent)
        and ``.producer_unique_id`` (child).
    """
    children: dict[NodeId, list[NodeId]] = {uid: [] for uid in nodes}
    for edge in edges:
        parent = edge.consumer_unique_id
        child = edge.producer_unique_id
        if parent in children:
            if child not in children[parent]:
                children[parent].append(child)
        # Ensure the child key exists even if not yet in nodes dict
        children.setdefault(child, [])
    return children


# ---------------------------------------------------------------------------
# Percentage helpers
# ---------------------------------------------------------------------------

def cumulative_percent(node, total_score: float) -> float:
    """Return node.cumulative_score / total_score * 100, or 0.0 on zero total."""
    if total_score == 0.0:
        return 0.0
    return node.cumulative_score / total_score * 100.0


def direct_percent(node, total_score: float) -> float:
    """Return node.direct_emissions_score / total_score * 100, or 0.0 on zero total."""
    if total_score == 0.0:
        return 0.0
    return node.direct_emissions_score / total_score * 100.0


def compute_node_tiers(
    nodes: dict,
    edges: list,
    root_uid: NodeId,
) -> dict[NodeId, int]:
    """Assign display tier by graph distance from the functional-unit root.

    The virtual demand node (``root_uid``) is omitted. Its direct children —
    the reference-flow activities — are **tier 0**; their suppliers are
    tier 1; and so on. This matches practitioner language ("tier-1 suppliers"
    = first inputs to the reference flow) and ``CONTEXT.md``.

    Do **not** use ``node.depth`` from ``bw_graph_tools`` after lazy
    ``traverse_from_node`` calls — that API resets the traversed node's depth
    to 0, so children are incorrectly labelled.
    """
    if root_uid not in nodes:
        return {}
    pcm = build_parent_child_map(nodes, edges)
    raw: dict[NodeId, int] = {root_uid: 0}
    queue: list[NodeId] = [root_uid]
    while queue:
        uid = queue.pop(0)
        for child_uid in pcm.get(uid, []):
            if child_uid in nodes and child_uid not in raw:
                raw[child_uid] = raw[uid] + 1
                queue.append(child_uid)
    # Shift: hide virtual root; reference flows become tier 0
    return {uid: tier - 1 for uid, tier in raw.items() if uid != root_uid}


# ---------------------------------------------------------------------------
# Expand policy / footer stats
# ---------------------------------------------------------------------------

EXPAND_MODES = ("tier", "path", "cumulative")


def _visible_contribution_nodes(
    nodes: dict,
    root_uid: NodeId | None = None,
) -> list:
    """Nodes shown in the contribution tree (skip the virtual demand root).

    Do not filter on Brightway ``node.depth`` — it is mutated to 0 before
    ``traverse_from_node`` and is not a reliable visibility signal.
    """
    if root_uid is not None:
        return [n for n in nodes.values() if n.unique_id != root_uid]
    return list(nodes.values())


def direct_impact_coverage(
    nodes: dict,
    total_score: float,
    root_uid: NodeId | None = None,
) -> float:
    """Σ(direct impact of visible nodes) / |total score|.

    Returns 0.0 when ``total_score`` is zero or there are no visible nodes.
    """
    if not nodes or total_score == 0.0:
        return 0.0
    direct_sum = sum(
        getattr(n, "direct_emissions_score", 0.0)
        for n in _visible_contribution_nodes(nodes, root_uid)
    )
    return direct_sum / abs(total_score)


def coverage_of_uids(
    nodes: dict,
    uids: set[NodeId],
    total_score: float,
) -> float:
    """Σ(direct impact of ``uids``) / |total score|."""
    if not uids or total_score == 0.0:
        return 0.0
    direct_sum = sum(
        getattr(nodes[uid], "direct_emissions_score", 0.0)
        for uid in uids
        if uid in nodes
    )
    return direct_sum / abs(total_score)


def plan_cumulative_expand(
    nodes: dict,
    edges: list,
    root_uid: NodeId,
    total_score: float,
    target_pct: float,
    visited: set,
    *,
    exclude: set | None = None,
) -> tuple[set[NodeId], set[NodeId], NodeId | None]:
    """Largest-first cumulative expand plan starting from reference flows.

    Opens included nodes with the largest **remaining upstream** impact
    (|cumulative| − |direct|). A node that is already almost entirely direct
    (little upstream left) is not auto-opened — its tiny children stay hidden
    until manual expand. When a node is opened, children are added
    largest-first until Σ(direct of included) / |total| reaches ``target_pct``.

    Returns
    -------
    included:
        Row unique_ids that should be in the tree model.
    to_expand:
        Unique_ids that should be visually expanded (opened during the walk).
    need_traverse:
        If not ``None``, this unvisited uid must be ``traverse_from_node``'d
        before the plan can continue; call again after traversing.
    """
    failed = exclude or set()
    pcm = build_parent_child_map(nodes, edges)
    included: set[NodeId] = {
        uid for uid in pcm.get(root_uid, []) if uid in nodes
    }
    walk_expanded: set[NodeId] = set()
    target = target_pct / 100.0
    abs_total = abs(total_score)

    def _coverage() -> float:
        return coverage_of_uids(nodes, included, total_score)

    def _remaining(n) -> float:
        cum = abs(getattr(n, "cumulative_score", 0.0))
        direct = abs(getattr(n, "direct_emissions_score", 0.0))
        return max(cum - direct, 0.0)

    def _worth_opening(n) -> bool:
        """Skip nodes whose impact is already almost all direct (dust upstream)."""
        rem = _remaining(n)
        if rem <= 0:
            return False
        cum = abs(getattr(n, "cumulative_score", 0.0))
        if cum > 0 and rem / cum < 0.05:
            return False
        if abs_total > 0 and rem / abs_total < 1e-9:
            return False
        return True

    def _can_open(uid: NodeId) -> bool:
        if uid in failed:
            return False
        node = nodes.get(uid)
        if node is None or not _worth_opening(node):
            return False
        if uid not in visited:
            return True
        return any(cid not in included for cid in pcm.get(uid, []))

    def _add_children_until_target(parent_uid: NodeId) -> None:
        """Add parent children largest-first; stop once coverage meets target."""
        children = [
            nodes[cid]
            for cid in pcm.get(parent_uid, [])
            if cid in nodes and cid not in included
        ]
        children.sort(
            key=lambda n: (_remaining(n), abs(getattr(n, "cumulative_score", 0.0)), -n.unique_id),
            reverse=True,
        )
        for child in children:
            included.add(child.unique_id)
            if _coverage() >= target:
                return

    while _coverage() < target:
        candidates = [
            nodes[uid]
            for uid in included
            if uid in nodes and uid not in walk_expanded and _can_open(uid)
        ]
        if not candidates:
            break
        pick = max(
            candidates,
            key=lambda n: (_remaining(n), abs(getattr(n, "cumulative_score", 0.0)), -n.unique_id),
        )
        uid = pick.unique_id
        if uid not in visited:
            return included, walk_expanded, uid

        walk_expanded.add(uid)
        _add_children_until_target(uid)

    return included, walk_expanded, None


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


def next_expand_candidates(
    nodes: dict,
    edges: list,
    visited: set,
    *,
    mode: str,
    value: float,
    total_score: float,
    root_uid: NodeId | None = None,
    exclude: set | None = None,
    eligible_ids: set | None = None,
) -> list[NodeId]:
    """Return unique_ids that the expand policy should open next.

    Parameters
    ----------
    mode:
        ``"tier"``, ``"path"``, or ``"cumulative"``.
    value:
        For tier: maximum tier (int). For path / cumulative: percent
        of |total| (0–100 UI scale).
    visited:
        ``state.visited_nodes`` — nodes already traversed.
    root_uid:
        Functional-unit node id; required for reliable tier mode (avoids
        trusting mutated ``node.depth``).
    exclude:
        Ids to skip (e.g. already failed to expand).
    eligible_ids:
        If set, only consider these ids (e.g. rows already in the tree model).
        Important for cumulative mode so we do not pick a globally largest
        unvisited node that is not yet in the view and cannot be expanded.

    Returns
    -------
    For ``tier`` / ``path``: all matching unvisited ids (any order).
    For ``cumulative``: at most one id (largest abs cumulative among
    unvisited), or ``[]`` when coverage already meets the target or nothing
    remains to expand.
    """
    if mode not in EXPAND_MODES:
        raise ValueError(f"Unknown expand mode: {mode!r}")

    skip = exclude or set()
    unvisited = [
        n for n in nodes.values()
        if n.unique_id not in visited
        and n.unique_id not in skip
        and (eligible_ids is None or n.unique_id in eligible_ids)
    ]

    if mode == "tier":
        max_tier = int(value)
        if root_uid is None:
            # Fallback: prefer original depth-0 FU id if still unique
            roots = [n for n in nodes.values() if getattr(n, "depth", None) == 0]
            root_uid = roots[0].unique_id if len(roots) == 1 else None
        if root_uid is None:
            return []
        tiers = compute_node_tiers(nodes, edges, root_uid)
        return [
            n.unique_id
            for n in unvisited
            if tiers.get(n.unique_id, max_tier + 1) < max_tier
        ]

    if mode == "path":
        if total_score == 0.0:
            return []
        threshold = abs(total_score) * (value / 100.0)
        return [
            n.unique_id
            for n in unvisited
            if abs(getattr(n, "cumulative_score", 0.0)) >= threshold
        ]

    # cumulative — one step, largest-first among eligible unvisited
    coverage = direct_impact_coverage(nodes, total_score, root_uid)
    if coverage >= (value / 100.0) or not unvisited:
        return []
    best = max(
        unvisited,
        key=lambda n: (
            abs(getattr(n, "cumulative_score", 0.0)),
            -n.unique_id,
        ),
    )
    return [best.unique_id]


def path_display_set(
    nodes: dict,
    edges: list,
    root_uid: NodeId,
    total_score: float,
    min_path_pct: float,
    visited: set,
) -> tuple[set[NodeId], set[NodeId]]:
    """Rows to show / expand for individual path-impact policy.

    * Auto-expand a node only if its path impact is ≥ ``min_path_pct`` **and**
      it has at least one child that is also ≥ ``min_path_pct`` (the high-impact
      path continues). Terminal high-impact nodes stay collapsed.
    * Under each auto-expanded node, list **all** discovered children (including
      below-threshold siblings). The engine cutoff already limits which children
      exist in ``edges``.

    Returns ``(included_uids, visually_expanded_uids)``.
    """
    pcm = build_parent_child_map(nodes, edges)
    threshold = abs(total_score) * (min_path_pct / 100.0) if total_score else 0.0

    def _above(uid: NodeId) -> bool:
        node = nodes.get(uid)
        if node is None:
            return False
        return abs(getattr(node, "cumulative_score", 0.0)) >= threshold

    high_path = {
        uid
        for uid, node in nodes.items()
        if uid != root_uid
        and uid in visited
        and _above(uid)
    }

    # Expand only while the high-impact path continues into a child
    to_expand = {
        uid
        for uid in high_path
        if any(_above(cid) for cid in pcm.get(uid, []))
    }

    included: set[NodeId] = {
        uid for uid in pcm.get(root_uid, []) if uid in nodes
    }
    included.update(high_path)
    for uid in to_expand:
        for cid in pcm.get(uid, []):
            if cid in nodes:
                included.add(cid)

    return included, to_expand


# ---------------------------------------------------------------------------
# Sunburst ring builder
# ---------------------------------------------------------------------------

def build_sunburst_rings(
    nodes: dict,
    edges: list,
    total_score: float,
    max_depth: int,
) -> list[list[dict]]:
    """Build per-depth ring data for a sunburst (layered donut) chart.

    Returns a list of rings, one per depth level from 1 to ``max_depth``.
    Each ring is a list of wedge dicts::

        {
            "unique_id": int,
            "label": str,           # activity name or "other"
            "share": float,         # fraction of *parent* arc (0–1)
            "cumulative_score": float,
            "is_other": bool,
        }

    Wedge ``share`` is ``node.cumulative_score / parent.cumulative_score``.
    An ``"other"`` wedge is appended when the children's shares don't sum to 1.

    Parameters
    ----------
    nodes:
        ``state.nodes`` dict.
    edges:
        ``state.edges`` list.
    total_score:
        ``lca.score`` — used only to guard against zero; not used for ring math.
    max_depth:
        Maximum tier depth to include (inclusive).
    """
    if not nodes or total_score == 0.0:
        return []

    parent_child = build_parent_child_map(nodes, edges)

    # Collect nodes by depth
    by_depth: dict[int, list] = {}
    for node in nodes.values():
        d = node.depth
        if 1 <= d <= max_depth:
            by_depth.setdefault(d, []).append(node)

    rings: list[list[dict]] = []

    for depth in range(1, max_depth + 1):
        depth_nodes = by_depth.get(depth, [])
        if not depth_nodes:
            break

        # Group by parent to compute "other" wedge per parent
        by_parent: dict[NodeId, list] = {}
        for node in depth_nodes:
            # Find this node's parent via edges
            parent_id = _find_parent(node.unique_id, edges)
            by_parent.setdefault(parent_id, []).append(node)

        ring: list[dict] = []
        for parent_id, children in by_parent.items():
            parent_node = nodes.get(parent_id)
            if parent_node is None:
                continue
            parent_score = parent_node.cumulative_score
            if parent_score == 0.0:
                continue

            children_score_sum = sum(c.cumulative_score for c in children)
            for child in children:
                share = child.cumulative_score / parent_score if parent_score else 0.0
                ring.append({
                    "unique_id": child.unique_id,
                    "label": getattr(child, "_label", str(child.unique_id)),
                    "share": share,
                    "cumulative_score": child.cumulative_score,
                    "parent_unique_id": parent_id,
                    "is_other": False,
                })

            # "other" wedge for the remainder
            remainder = parent_score - children_score_sum
            if abs(remainder) > abs(parent_score) * 1e-9:
                ring.append({
                    "unique_id": None,
                    "label": "other",
                    "share": remainder / parent_score,
                    "cumulative_score": remainder,
                    "parent_unique_id": parent_id,
                    "is_other": True,
                })

        if ring:
            rings.append(ring)

    return rings


def _find_parent(child_uid: NodeId, edges: list) -> NodeId | None:
    """Return the consumer_unique_id of the edge whose producer is child_uid."""
    for edge in edges:
        if edge.producer_unique_id == child_uid:
            return edge.consumer_unique_id
    return None


# ---------------------------------------------------------------------------
# Export flattening
# ---------------------------------------------------------------------------

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
