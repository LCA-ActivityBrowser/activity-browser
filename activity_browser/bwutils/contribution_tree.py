"""Pure data-preparation helpers for the Contribution Tree tab.

These functions transform a ``SameNodeEachVisitGraphTraversal`` state object
(or any object with compatible ``.nodes`` and ``.edges`` attributes) into the
data structures consumed by the tree item model, the sunburst plot, and the
table export.  No Qt dependency — fully testable with plain fake objects.
"""

from __future__ import annotations

import math
import warnings
from collections import defaultdict
from contextlib import contextmanager
from typing import Callable, Iterable

import pandas as pd


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
        warnings.filterwarnings(
            "ignore",
            message=r"Stopping traversal due to calculation count\.",
            category=UserWarning,
        )
        yield


def _metadata_codes(frame: pd.DataFrame) -> pd.Series | None:
    """Activity ``code`` from a column, MultiIndex, or ``key`` tuples."""
    if "code" in frame.columns:
        return frame["code"]
    names = list(getattr(frame.index, "names", None) or [])
    if isinstance(frame.index, pd.MultiIndex) and "code" in names:
        return pd.Series(frame.index.get_level_values("code"), index=frame.index)
    if "key" in frame.columns:
        def _code(key) -> str:
            if isinstance(key, (tuple, list)) and len(key) >= 2:
                return "" if key[1] is None else str(key[1])
            return ""
        return frame["key"].map(_code)
    return None


def activity_metadata_for_ids(
    ids: Iterable[int],
    dataframe: pd.DataFrame | None = None,
) -> dict[int, dict]:
    """Map datapackage ids to labels from a MetaDataStore dataframe."""
    wanted = set()
    for i in ids:
        try:
            n = int(i)
        except (TypeError, ValueError):
            continue
        if n >= 0:
            wanted.add(n)
    if not wanted or dataframe is None or "id" not in getattr(dataframe, "columns", []):
        return {}
    mask = dataframe["id"].isin(wanted)
    sub = dataframe.loc[mask].copy()
    if sub.empty:
        return {}
    codes = _metadata_codes(sub)
    if codes is not None and "code" not in sub.columns:
        sub["code"] = codes
    cols = [
        c for c in ("id", "name", "product", "location", "database", "unit", "code")
        if c in sub.columns
    ]
    sub = sub[cols]
    text = [c for c in sub.columns if c != "id"]
    sub[text] = sub[text].fillna("")
    out: dict[int, dict] = {}
    for rec in sub.fillna("").to_dict("records"):
        aid = int(rec["id"])
        name = rec.get("name") or ""
        out[aid] = {
            "product": rec.get("product") or name,
            "name": name,
            "location": rec.get("location") or "",
            "database": rec.get("database") or "",
            "unit": rec.get("unit") or "",
            "code": rec.get("code") or "",
        }
    return out


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
# Adjust policy / footer stats
# ---------------------------------------------------------------------------

# Modes accepted by :func:`next_expand_candidates` (traversal probing only).
# Cumulative adjust uses :func:`plan_cumulative_expand` instead.
CANDIDATE_ADJUST_MODES = ("tier", "path")


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


def _node_direct_score(node, direct_lookup: Callable[[NodeId], float] | None = None) -> float:
    """Visit-level direct, or ``direct_lookup(unique_id)`` when provided."""
    if node is None:
        return 0.0
    if direct_lookup is not None:
        return float(direct_lookup(node.unique_id) or 0.0)
    return float(getattr(node, "direct_emissions_score", 0.0) or 0.0)


def coverage_of_uids(
    nodes: dict,
    uids: set[NodeId],
    total_score: float,
    *,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> float:
    """Σ(direct impact of ``uids``) / |total score|."""
    if not uids or total_score == 0.0:
        return 0.0
    direct_sum = sum(
        _node_direct_score(nodes[uid], direct_lookup)
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
    eligible_ids: set | None = None,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> tuple[set[NodeId], set[NodeId], NodeId | None]:
    """Largest-first cumulative expand plan starting from reference flows.

    Opens included nodes with the largest **remaining upstream** impact
    (|cumulative| − |direct|). When a node is opened, children that raise
    coverage are added largest-direct first until Σ(direct of included) /
    |total| reaches ``target_pct``. Zero-direct siblings are not dumped into
    the display set: only the next remaining-upstream hop is added, then that
    hop is opened before leftover siblings of the parent. A 0-direct child is
    skipped when an already-included sibling still carries more remaining
    upstream (follow that plant, not leftover markets), and a parent that
    already has a direct-impact child plus one 0-direct hop does not gain
    extra 0-direct siblings. A node with no remaining upstream is not opened.
    Cumulative Adjust does not skip “mostly direct” nodes with a
    remaining-upstream ratio. ``direct_lookup`` (Sankey) uses solved-inventory
    directs per unique process so coverage matches the boxes on screen.

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

    def _ok(uid: NodeId) -> bool:
        return eligible_ids is None or uid in eligible_ids

    included: set[NodeId] = {
        uid for uid in pcm.get(root_uid, []) if uid in nodes and _ok(uid)
    }
    walk_expanded: set[NodeId] = set()
    target = target_pct / 100.0
    abs_total = abs(total_score)

    def _coverage() -> float:
        return coverage_of_uids(
            nodes, included, total_score, direct_lookup=direct_lookup
        )

    def _direct(n) -> float:
        return abs(_node_direct_score(n, direct_lookup))

    def _remaining(n) -> float:
        cum = abs(getattr(n, "cumulative_score", 0.0))
        return max(cum - _direct(n), 0.0)

    def _worth_opening(n) -> bool:
        rem = _remaining(n)
        if rem <= 0:
            return False
        if abs_total > 0 and rem / abs_total < 1e-9:
            return False
        return True

    def _contributes(n) -> bool:
        direct = _direct(n)
        return direct > 0 and (abs_total <= 0 or direct / abs_total >= 1e-9)

    def _skip_zero_direct_sibling(parent_uid: NodeId, child) -> bool:
        """Hide leftover 0-direct markets beside plants that already add impact."""
        kids = [
            cid
            for cid in pcm.get(parent_uid, [])
            if cid in included and cid in nodes and cid != child.unique_id
        ]
        contributing = [cid for cid in kids if _contributes(nodes[cid])]
        zero_hops = [cid for cid in kids if not _contributes(nodes[cid])]
        if not contributing:
            return False
        if zero_hops:
            return True
        return any(_remaining(nodes[cid]) > _remaining(child) for cid in contributing)

    def _useful_child(cid: NodeId, parent_uid: NodeId) -> bool:
        if cid not in nodes or cid in included or not _ok(cid):
            return False
        child = nodes[cid]
        if _contributes(child):
            return True
        if not _worth_opening(child):
            return False
        return not _skip_zero_direct_sibling(parent_uid, child)

    def _can_open(uid: NodeId) -> bool:
        if uid in failed:
            return False
        node = nodes.get(uid)
        if node is None or not _worth_opening(node):
            return False
        if uid not in visited:
            return True
        return any(_useful_child(cid, uid) for cid in pcm.get(uid, []))

    def _add_children_until_target(parent_uid: NodeId) -> None:
        """Add coverage-raising children; at most one 0-direct hop per call."""
        children = [
            nodes[cid]
            for cid in pcm.get(parent_uid, [])
            if cid in nodes and cid not in included and _ok(cid)
        ]
        children.sort(
            key=lambda n: (
                _direct(n),
                _remaining(n),
                abs(getattr(n, "cumulative_score", 0.0)),
                -n.unique_id,
            ),
            reverse=True,
        )
        for child in children:
            if _coverage() >= target:
                return
            if _contributes(child):
                included.add(child.unique_id)
                continue
            if _worth_opening(child):
                if _skip_zero_direct_sibling(parent_uid, child):
                    continue
                included.add(child.unique_id)
                return

    def _rank(n) -> tuple:
        return (_remaining(n), abs(getattr(n, "cumulative_score", 0.0)), -n.unique_id)

    while _coverage() < target:
        hops = [
            nodes[uid]
            for uid in included
            if uid in nodes and uid not in walk_expanded and _can_open(uid)
        ]
        if hops:
            pick = max(hops, key=_rank)
            uid = pick.unique_id
            if uid not in visited:
                return included, walk_expanded, uid
            walk_expanded.add(uid)
            _add_children_until_target(uid)
            continue
        more = [
            nodes[uid]
            for uid in walk_expanded
            if uid in nodes and _can_open(uid)
        ]
        if not more:
            break
        before = len(included)
        _add_children_until_target(max(more, key=_rank).unique_id)
        if len(included) == before:
            break

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
    """Return unique_ids still needing ``traverse_from_node`` for tier/path.

    Cumulative impact expand must use :func:`plan_cumulative_expand` (display
    set + remaining-upstream ranking). Individual path *display* / visual
    expand uses :func:`path_display_set`; this helper only probes which
    unvisited nodes to calculate so the display set can be built.

    Parameters
    ----------
    mode:
        ``"tier"`` or ``"path"`` only.
    value:
        For tier: maximum tier (int). For path: percent of |total| (0–100).
    visited:
        ``state.visited_nodes`` — nodes already traversed.
    root_uid:
        Functional-unit node id; required for reliable tier mode (avoids
        trusting mutated ``node.depth``).
    exclude:
        Ids to skip (e.g. already failed to expand).
    eligible_ids:
        If set, only consider these ids.

    Returns
    -------
    Matching unvisited ids (any order).
    """
    if mode not in CANDIDATE_ADJUST_MODES:
        raise ValueError(
            f"Unknown adjust mode: {mode!r} "
            f"(use plan_cumulative_expand for cumulative)"
        )

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

    # path — calculate nodes at/above threshold; display uses path_display_set
    if total_score == 0.0:
        return []
    threshold = abs(total_score) * (value / 100.0)
    return [
        n.unique_id
        for n in unvisited
        if abs(getattr(n, "cumulative_score", 0.0)) >= threshold
    ]


def safe_traverse_from_node(state, unique_id: NodeId, depth: int = 1) -> bool:
    """Zero ``node.depth``, suppress coverage warnings, then ``traverse_from_node``.

    Brightway derives relative max depth from the current ``node.depth`` before
    resetting it; mid-tree expands must start at depth 0 so ``depth=1`` means
    one edge.
    """
    if unique_id in state.visited_nodes:
        return False
    node = state.nodes.get(unique_id)
    if node is None:
        return False
    node.depth = 0
    with suppress_graph_traversal_warnings():
        return bool(state.traverse_from_node(unique_id, depth=depth))


def run_expand_policy(
    state,
    *,
    mode: str,
    value: float,
    total_score: float,
    on_progress=None,
    unique_activities: bool = False,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> tuple[set[NodeId] | None, set[NodeId] | None]:
    """Traverse for an adjust policy; return display-set ``(included, to_expand)``.

    For ``tier`` / ``path``: traverse via :func:`next_expand_candidates`.
    For ``path``: also return :func:`path_display_set`.
    For ``cumulative``: loop :func:`plan_cumulative_expand` until done.
    ``unique_activities`` (Sankey) only opens the **highest-path** visit of
    each process (one box; a small first NNEV visit must not hide a later
    large path).

    ``on_progress(step, n_nodes)`` is optional (e.g. UI busy tick). If it
    returns ``False``, stop and return the display set for the graph so far.
    Returns ``(None, None)`` for tier (caller opens view by max tier).
    """
    root_uid = state._root_node.unique_id
    failed: set[NodeId] = set()

    def _stop(step: int) -> bool:
        return on_progress is not None and on_progress(step, len(state.nodes)) is False

    def _eligible() -> set[NodeId] | None:
        if not unique_activities:
            return None
        return keep_best_visit_per_activity(
            state.nodes,
            state.edges,
            {uid for uid in state.nodes if uid != root_uid},
            root_uid,
        )

    if mode == "cumulative":
        included: set[NodeId] = set()
        to_expand: set[NodeId] = set()
        for step in range(10_000):
            included, to_expand, need = plan_cumulative_expand(
                state.nodes,
                state.edges,
                root_uid,
                total_score,
                value,
                state.visited_nodes,
                exclude=failed,
                eligible_ids=_eligible(),
                direct_lookup=direct_lookup,
            )
            if need is None:
                break
            if _stop(step):
                break
            if not safe_traverse_from_node(state, need):
                failed.add(need)
        if unique_activities:
            included = keep_best_visit_per_activity(
                state.nodes, state.edges, included, root_uid
            )
        return included, to_expand

    # tier / path — calculate first
    stopped = False
    for step in range(10_000):
        candidates = next_expand_candidates(
            state.nodes,
            state.edges,
            state.visited_nodes,
            mode=mode,
            value=value,
            total_score=total_score,
            root_uid=root_uid,
            exclude=failed,
            eligible_ids=_eligible(),
        )
        if not candidates:
            break
        made_progress = False
        for uid in candidates:
            if _stop(step):
                stopped = True
                break
            if safe_traverse_from_node(state, uid):
                made_progress = True
            else:
                failed.add(uid)
        if stopped or not made_progress:
            break

    if mode == "path":
        included, to_expand = path_display_set(
            state.nodes,
            state.edges,
            root_uid,
            total_score,
            value,
            state.visited_nodes,
        )
        if unique_activities:
            included = keep_best_visit_per_activity(
                state.nodes, state.edges, included, root_uid
            )
        return included, to_expand
    return None, None


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
    * Hide siblings that are not themselves on a ≥ ``min_path_pct`` path.
      Show all (footer) reveals the rest of the calculated graph.

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
        uid for uid in pcm.get(root_uid, []) if uid in nodes and _above(uid)
    }
    included.update(high_path)
    for uid in to_expand:
        for cid in pcm.get(uid, []):
            if cid in nodes and _above(cid):
                included.add(cid)

    return included, to_expand


def graph_display_set(
    nodes: dict,
    edges: list,
    *,
    mode: str,
    value: float,
    total_score: float,
    root_uid: NodeId,
    visited: set | None = None,
    unique_activities: bool = False,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> tuple[set[NodeId], set[NodeId]]:
    """Display set for a calculated graph (Tree plot or Sankey) from Adjust policy.

    Does not traverse. ``tier`` uses :func:`compute_node_tiers`; ``path`` and
    ``cumulative`` reuse the Tree policies on the nodes already in ``nodes``.
    ``unique_activities`` (Sankey) plans on the **highest-path** visit of each
    process so Individual path impact follows the large path, not a small
    first NNEV visit of the same process.
    """
    visited_set = set(visited) if visited is not None else set(nodes)
    eligible = None
    if unique_activities and mode == "cumulative":
        eligible = keep_best_visit_per_activity(
            nodes,
            edges,
            {uid for uid in nodes if uid != root_uid},
            root_uid,
        )
    if mode == "tier":
        max_tier = max(0, int(value))
        tiers = compute_node_tiers(nodes, edges, root_uid)
        included = {uid for uid, tier in tiers.items() if 0 <= tier <= max_tier}
        pcm = build_parent_child_map(nodes, edges)
        to_expand = {
            uid
            for uid in included
            if any(cid in included for cid in pcm.get(uid, []))
        }
    elif mode == "path":
        included, to_expand = path_display_set(
            nodes, edges, root_uid, total_score, value, visited_set
        )
    else:
        included, to_expand, _need = plan_cumulative_expand(
            nodes,
            edges,
            root_uid,
            total_score,
            value,
            visited_set,
            eligible_ids=eligible,
            direct_lookup=direct_lookup,
        )
    if unique_activities:
        included = keep_best_visit_per_activity(nodes, edges, included, root_uid)
    return included, to_expand


def _activity_id(node) -> int | None:
    """Process datapackage id, or ``None`` for the virtual demand root."""
    if node is None:
        return None
    uid = getattr(node, "unique_id", None)
    if uid is not None and uid < 0:
        return None
    aid = getattr(node, "activity_datapackage_id", None)
    return aid


def _int_or_none(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nonneg_int(value) -> int | None:
    n = _int_or_none(value)
    if n is None or n < 0:
        return None
    return n


def _node_by_uid(nodes: dict | None, uid) -> object | None:
    """Traversal node for a visit id, accepting int or digit-string keys."""
    if not nodes or uid is None:
        return None
    key = _int_or_none(uid)
    if key is None:
        return None
    node = nodes.get(key)
    if node is not None:
        return node
    node = nodes.get(uid)
    if node is not None:
        return node
    for k, v in nodes.items():
        if _int_or_none(k) == key:
            return v
    return None


def _payload_open_ref(
    activity_id=None,
    database: str | None = None,
    code: str | None = None,
) -> dict:
    ref: dict = {}
    aid = _nonneg_int(activity_id)
    if aid is not None:
        ref["activity_id"] = aid
    db = str(database or "").strip()
    cd = str(code or "").strip()
    if db:
        ref["database"] = db
    if cd:
        ref["code"] = cd
    return ref


def open_process_refs(
    *,
    is_aggregate: bool = False,
    activity_id=None,
    database: str | None = None,
    code: str | None = None,
    nodes: dict | None = None,
    uid: NodeId | None = None,
    constituent_uids: list | None = None,
) -> list[dict]:
    """Identity refs for **Open process** on a shown Tree or Sankey box.

    The traversal visit is the source of truth (not a JS datapackage id that
    may be a visit uid). Aggregates are a group of processes — Open process
    is disabled. Payload ``database`` / ``code`` are fallbacks when Brightway
    ``get_node(id=)`` cannot resolve the visit.
    """
    if is_aggregate:
        return []
    payload = _payload_open_ref(activity_id, database, code)
    visit = _node_by_uid(nodes, uid)
    if visit is not None:
        uid_i = _int_or_none(getattr(visit, "unique_id", None))
        aid = _nonneg_int(getattr(visit, "activity_datapackage_id", None))
        if uid_i is not None and uid_i < 0 and aid is None:
            return [payload] if payload else []
        ref = dict(payload)
        if aid is not None:
            ref["activity_id"] = aid
        return [ref] if ref else []
    return [payload] if payload else []


def activities_from_open_refs(refs: list[dict]) -> list:
    """Brightway nodes for Open process refs (product/waste → processor)."""
    import bw2data as bd
    import bw_functional as bf

    from activity_browser.bwutils.commontasks import refresh_node

    out = []
    seen: set = set()
    for ref in refs or []:
        node = None
        aid = ref.get("activity_id")
        if aid is not None:
            try:
                node = bd.get_node(id=int(aid))
            except Exception:
                node = None
        if node is None:
            db = str(ref.get("database") or "").strip()
            code = str(ref.get("code") or "").strip()
            if db and code:
                try:
                    node = bd.get_activity((db, code))
                except Exception:
                    node = None
        if node is None:
            continue
        try:
            node = refresh_node(node)
        except Exception:
            pass
        try:
            if isinstance(node, bf.Product):
                node = refresh_node(node["processor"])
            else:
                waste_cls = getattr(bf, "Waste", None)
                if waste_cls is not None and isinstance(node, waste_cls):
                    node = refresh_node(node["processor"])
        except Exception:
            continue
        key = getattr(node, "key", None) or id(node)
        if key in seen:
            continue
        seen.add(key)
        out.append(node)
    return out


def open_process_activity_id(
    *,
    is_aggregate: bool = False,
    activity_id=None,
    nodes: dict | None = None,
    uid: NodeId | None = None,
    constituent_uids: list | None = None,
) -> int | None:
    """Datapackage id for **Open process**, or ``None`` when there is no process.

    Prefer the traversal visit over a JS ``activity_id``. Aggregates have no
    single process to open.
    """
    refs = open_process_refs(
        is_aggregate=is_aggregate,
        activity_id=activity_id,
        nodes=nodes,
        uid=uid,
        constituent_uids=constituent_uids,
    )
    if not refs:
        return None
    return refs[0].get("activity_id")


def visits_of_same_activity(nodes: dict, uid: NodeId) -> list[NodeId]:
    """NNEV visit ids of the same process as ``uid`` (clicked visit first).

    Unique-process Sankey draws one box; other visits of that process can still
    hold cutoff suppliers the representative visit never listed.
    """
    if uid not in nodes:
        return []
    aid = _activity_id(nodes.get(uid))
    if aid is None:
        return [uid]
    out = [u for u, node in nodes.items() if _activity_id(node) == aid]
    if uid in out:
        out.remove(uid)
        out.insert(0, uid)
    return out


def supplier_visit_ids(
    pcm: dict[NodeId, list[NodeId]],
    nodes: dict,
    uid: NodeId,
    *,
    unique_activities: bool = False,
) -> list[NodeId]:
    """Supplier visit ids of ``uid``, or of every visit of that process."""
    if not unique_activities:
        return [cid for cid in pcm.get(uid, []) if cid in nodes]
    seen: set[NodeId] = set()
    out: list[NodeId] = []
    for visit in visits_of_same_activity(nodes, uid):
        for cid in pcm.get(visit, []):
            if cid in nodes and cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


def unopened_same_activity_hops(
    nodes: dict,
    uid: NodeId,
    opened: set[NodeId] | None,
) -> list[NodeId]:
    """Unopened same-process visits that still have remaining upstream."""
    opened_set = set(opened) if opened is not None else set(nodes)
    hops: list[NodeId] = []
    for visit in visits_of_same_activity(nodes, uid):
        if visit in opened_set:
            continue
        node = nodes.get(visit)
        if node is None:
            continue
        rem = max(
            abs(getattr(node, "cumulative_score", 0.0))
            - abs(getattr(node, "direct_emissions_score", 0.0)),
            0.0,
        )
        if rem > 0:
            hops.append(visit)
    return hops


def keep_best_visit_per_activity(
    nodes: dict,
    edges: list,
    included: set[NodeId],
    root_uid: NodeId,
) -> set[NodeId]:
    """Keep one visit per process: the included visit with largest |path impact|.

    NNEV may discover a process first via a small path (e.g. a minor exchange
    to the reference flow) and later via a large path. Unique-process Sankey
    must draw and hop the large path, or Individual path impact stops on a box
    whose only calculated suppliers are the small visit's. Circular supply
    (A→B→A) still yields two boxes: the later visit of A has a smaller path
    impact than the first, so it is dropped.

    ``edges`` is unused (call-site stability). Selection is by |path impact|
    among ``included``, not first-visit / BFS order from ``root_uid``.
    """
    best: dict[int, NodeId] = {}
    extra: set[NodeId] = set()
    for uid in included:
        if uid == root_uid or uid not in nodes:
            continue
        node = nodes[uid]
        aid = _activity_id(node)
        if aid is None:
            extra.add(uid)
            continue
        prev = best.get(aid)
        if prev is None or _visit_path_rank(node) > _visit_path_rank(nodes[prev]):
            best[aid] = uid
    return extra | set(best.values())


def _visit_path_rank(node) -> tuple:
    """Higher is a better unique-process representative."""
    return (abs(getattr(node, "cumulative_score", 0.0)), -int(node.unique_id))


def unique_process_stats(
    nodes: dict,
    edges: list,
    root_uid: NodeId,
    total_score: float,
    included: set[NodeId] | None = None,
    *,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> dict:
    """Shown vs calculated unique-process counts, coverage, and max tier."""
    universe = {uid for uid in nodes if uid != root_uid}
    calculated = keep_best_visit_per_activity(nodes, edges, universe, root_uid)
    shown = keep_best_visit_per_activity(
        nodes, edges, set(included) if included is not None else calculated, root_uid
    )
    tiers = compute_node_tiers(nodes, edges, root_uid)
    return {
        "shown_n": len(shown),
        "shown_cov": coverage_of_uids(
            nodes, shown, total_score, direct_lookup=direct_lookup
        ),
        "shown_tier": max((tiers.get(uid, 0) for uid in shown), default=0),
        "calc_n": len(calculated),
        "calc_cov": coverage_of_uids(
            nodes, calculated, total_score, direct_lookup=direct_lookup
        ),
        "calc_tier": max((tiers.get(uid, 0) for uid in calculated), default=0),
    }


def _display_ancestors(
    pcm: dict[NodeId, list[NodeId]],
    root_uid: NodeId,
    uid: NodeId,
    drawn: set[NodeId],
) -> set[NodeId]:
    """Drawn nodes on a path from ``root_uid`` to ``uid`` (excluding ``uid``)."""
    parent: dict[NodeId, NodeId] = {}
    seen = {root_uid}
    queue = [root_uid]
    found = False
    while queue:
        cur = queue.pop(0)
        for child in pcm.get(cur, []):
            if child not in drawn or child in seen:
                continue
            seen.add(child)
            parent[child] = cur
            if child == uid:
                found = True
                queue = []
                break
            queue.append(child)
    if not found:
        return set()
    out: set[NodeId] = set()
    cur = uid
    while cur in parent:
        cur = parent[cur]
        if cur in drawn:
            out.add(cur)
    return out


def toggle_graph_display_node(
    included: set[NodeId],
    nodes: dict,
    edges: list,
    uid: NodeId,
    *,
    unique_activities: bool = False,
    root_uid: NodeId | None = None,
) -> set[NodeId]:
    """Expand or collapse one visit in a calculated graph display set.

    Manual expand shows every unique-process supplier already in the calculated
    graph (engine cutoff). Adjust-hidden siblings come back on expand.
    Collapse runs only when those suppliers are already shown. Already-drawn
    processes stay one box (no cycle unroll).
    """
    pcm = build_parent_child_map(nodes, edges)
    children = supplier_visit_ids(
        pcm, nodes, uid, unique_activities=unique_activities
    )
    if not children:
        return set(included)
    if unique_activities:
        root = root_uid if root_uid is not None else next(
            (i for i in nodes if i < 0), -1
        )
        drawn = keep_best_visit_per_activity(nodes, edges, set(included), root)
        drawn_acts = {
            _activity_id(nodes[u])
            for u in drawn
            if u in nodes and _activity_id(nodes[u]) is not None
        }
        shown_unique = []
        to_add = []
        for cid in children:
            aid = _activity_id(nodes.get(cid))
            if aid is not None and aid in drawn_acts:
                first = next(
                    (u for u in drawn if _activity_id(nodes.get(u)) == aid),
                    None,
                )
                if first is not None and first not in shown_unique:
                    shown_unique.append(first)
            elif cid not in drawn:
                to_add.append(cid)
        ancestors = _display_ancestors(pcm, root, uid, drawn)
        exclusive = [s for s in shown_unique if s not in ancestors and s != uid]
        if to_add:
            return set(included) | set(to_add)
        if exclusive:
            hide: set[NodeId] = set()
            stack = list(exclusive)
            while stack:
                cur = stack.pop()
                if cur in hide or cur in ancestors or cur == uid:
                    continue
                hide.add(cur)
                for child in pcm.get(cur, []):
                    mapped = child
                    aid = _activity_id(nodes.get(child))
                    if aid is not None:
                        mapped = next(
                            (u for u in drawn if _activity_id(nodes.get(u)) == aid),
                            child,
                        )
                    if mapped not in hide:
                        stack.append(mapped)
            return set(included) - hide
        return set(included)
    shown_children = [cid for cid in children if cid in included]
    if shown_children:
        return set(included) - _descendant_uids(pcm, uid)
    return set(included) | set(children)


def apply_graph_display_click(
    included: set[NodeId],
    nodes: dict,
    edges: list,
    uid: NodeId,
    *,
    unique_activities: bool = False,
    opened: set[NodeId] | None = None,
    root_uid: NodeId | None = None,
) -> tuple[set[NodeId], NodeId | None]:
    """Toggle the display set, or request a one-hop traverse of ``uid``.

    Returns ``(included, hop_uid)``. ``hop_uid`` is set when this process still
    has an unopened visit with remaining upstream (the clicked visit if that
    one is unopened). The caller hops every
    :func:`unopened_same_activity_hops` visit, then
    :func:`include_new_unique_suppliers`.
    """
    opened_set = set(opened) if opened is not None else set(nodes)
    if unique_activities:
        hops = unopened_same_activity_hops(nodes, uid, opened_set)
        if hops:
            return set(included), hops[0]
    else:
        node = nodes.get(uid)
        rem = 0.0
        if node is not None:
            rem = max(
                abs(getattr(node, "cumulative_score", 0.0))
                - abs(getattr(node, "direct_emissions_score", 0.0)),
                0.0,
            )
        if uid not in opened_set and rem > 0:
            return set(included), uid
    return (
        toggle_graph_display_node(
            included,
            nodes,
            edges,
            uid,
            unique_activities=unique_activities,
            root_uid=root_uid,
        ),
        None,
    )


def include_new_unique_suppliers(
    included: set[NodeId],
    nodes: dict,
    edges: list,
    uid: NodeId,
    *,
    root_uid: NodeId,
) -> set[NodeId]:
    """Add unique-process suppliers of ``uid`` discovered after a hop.

    Engine cutoff already limits which children exist. Does not apply Adjust
    path/cumulative filters. Unions suppliers of every NNEV visit of this
    process so a small first visit cannot hide another visit's suppliers.
    """
    pcm = build_parent_child_map(nodes, edges)
    drawn = keep_best_visit_per_activity(nodes, edges, set(included), root_uid)
    drawn_acts = {
        _activity_id(nodes[u])
        for u in drawn
        if u in nodes and _activity_id(nodes[u]) is not None
    }
    to_add = [
        cid
        for cid in supplier_visit_ids(pcm, nodes, uid, unique_activities=True)
        if _activity_id(nodes.get(cid)) not in drawn_acts
    ]
    return set(included) | set(to_add)


# ---------------------------------------------------------------------------
# Direct-impact colour (matches Contribution Tree table blue/green tint)
# ---------------------------------------------------------------------------

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


def _parent_uid(child_uid: NodeId, edges: list, root_uid: NodeId) -> NodeId:
    parent = _find_parent(child_uid, edges)
    return root_uid if parent is None else parent


def _upstream_layout_span(
    span: float,
    cumulative_score: float,
    direct_emissions_score: float,
) -> float:
    """Horizontal span available for upstream children (excludes parent direct).

    Uses ``|cumulative − direct|`` so credits that make ``|direct| > |cumulative|``
    still receive a positive band (same magnitude as the net upstream share).
    """
    if span <= 0 or not cumulative_score:
        return 0.0
    upstream_abs = abs(cumulative_score - direct_emissions_score)
    return span * (upstream_abs / abs(cumulative_score))


# ---------------------------------------------------------------------------
# Supply-chain layout (sunburst / vertical tiers / horizontal tiers)
# ---------------------------------------------------------------------------

def build_chain_layout(
    nodes: dict,
    edges: list,
    total_score: float,
    max_depth: int,
    root_uid: NodeId | None = None,
    metadata_lookup: Callable[[int], dict] | None = None,
    included_uids: set[NodeId] | None = None,
) -> list[dict]:
    """Parent-aligned layout segments for contribution-tree plots.

    Each segment has ``tier``, ``x0``/``x1`` in ``[0, 1]``, impact scores,
    and activity metadata. Tier-0 (reference flow) nodes only — not every
    virtual-root child.

    When ``included_uids`` is set, only those nodes appear and visible
    siblings reflow within each parent's upstream (non-direct) span.
    """
    if not nodes or total_score == 0.0 or max_depth <= 0:
        return []

    if root_uid is None:
        roots = [n for n in nodes.values() if getattr(n, "depth", None) == 0]
        if len(roots) != 1:
            return []
        root_uid = roots[0].unique_id

    pcm = build_parent_child_map(nodes, edges)
    tiers = compute_node_tiers(nodes, edges, root_uid)
    segments: list[dict] = []

    def is_included(uid: NodeId) -> bool:
        return included_uids is None or uid in included_uids

    def meta_for(node) -> dict:
        if metadata_lookup is None:
            return {}
        return metadata_lookup(getattr(node, "activity_datapackage_id", None)) or {}

    def append_segment(node, x0: float, x1: float) -> None:
        if not is_included(node.unique_id):
            return
        tier = tiers.get(node.unique_id)
        if tier is None or tier >= max_depth:
            return
        act_meta = meta_for(node)
        product = act_meta.get("product") or getattr(node, "_label", str(node.unique_id))
        aid = getattr(node, "activity_datapackage_id", None)
        rec = {
            "unique_id": node.unique_id,
            "tier": tier,
            "x0": x0,
            "x1": x1,
            "product": product,
            "process": act_meta.get("name", ""),
            "location": act_meta.get("location", ""),
            "database": act_meta.get("database", ""),
            "code": act_meta.get("code", ""),
            "unit": act_meta.get("unit", ""),
            "cumulative_score": node.cumulative_score,
            "direct_emissions_score": node.direct_emissions_score,
            "cumulative_pct": cumulative_percent(node, total_score),
            "direct_pct": direct_percent(node, total_score),
        }
        if aid is not None and aid >= 0:
            rec["activity_id"] = int(aid)
        segments.append(rec)

    def walk_children(parent_node, x0: float, x1: float, tier: int) -> None:
        child_tier = tier + 1
        if child_tier >= max_depth:
            return
        children = [
            nodes[c]
            for c in pcm.get(parent_node.unique_id, [])
            if c in nodes and is_included(c)
        ]
        children.sort(key=lambda n: abs(n.cumulative_score), reverse=True)
        if not children:
            return
        x = x0
        span = x1 - x0
        layout_span = _upstream_layout_span(
            span,
            parent_node.cumulative_score,
            parent_node.direct_emissions_score,
        )
        if included_uids is None:
            denom = abs(parent_node.cumulative_score)
            for child in children:
                share = abs(child.cumulative_score) / denom if denom else 0.0
                w = share * span
                append_segment(child, x, x + w)
                walk_children(child, x, x + w, child_tier)
                x += w
        else:
            child_total = sum(abs(c.cumulative_score) for c in children)
            for child in children:
                share = abs(child.cumulative_score) / child_total if child_total else 0.0
                w = share * layout_span
                append_segment(child, x, x + w)
                walk_children(child, x, x + w, child_tier)
                x += w

    tier0 = [
        nodes[uid]
        for uid in pcm.get(root_uid, [])
        if uid in nodes and tiers.get(uid) == 0 and is_included(uid)
    ]
    tier0.sort(key=lambda n: abs(n.cumulative_score), reverse=True)

    x = 0.0
    if included_uids is None:
        denom = abs(total_score)
        for node in tier0:
            share = abs(node.cumulative_score) / denom if denom else 0.0
            append_segment(node, x, x + share)
            walk_children(node, x, x + share, 0)
            x += share
    else:
        tier0_total = sum(abs(n.cumulative_score) for n in tier0)
        for node in tier0:
            share = (
                abs(node.cumulative_score) / tier0_total
                if tier0_total
                else 0.0
            )
            append_segment(node, x, x + share)
            walk_children(node, x, x + share, 0)
            x += share

    return segments


# Plot aggregation (sibling merge under each parent; plot-only display)
PLOT_AGGREGATE_FIELDS = ("product", "name", "location", "unit", "database")

PLOT_AGGREGATE_LABELS = {
    "product": "Product",
    "name": "Process",
    "location": "Location",
    "unit": "Unit",
    "database": "Database",
}


def plot_click_target_uid(segment: dict) -> int:
    """Tree ``unique_id`` to toggle when a plot segment is clicked."""
    return int(segment.get("toggle_uid", segment["unique_id"]))


D3_PLOT_MODES = ("icicle", "tier_bars", "sunburst", "treemap")

_D3_SEGMENT_FIELDS = (
    "unique_id",
    "toggle_uid",
    "tier",
    "x0",
    "x1",
    "product",
    "process",
    "location",
    "database",
    "code",
    "unit",
    "cumulative_score",
    "direct_emissions_score",
    "cumulative_pct",
    "direct_pct",
    "is_aggregate",
    "aggregate_key",
    "aggregate_by",
    "constituent_uids",
    "constituent_products",
    "activity_id",
)


def format_impact_abs(value: float) -> str:
    """Compact absolute score for plot tooltips."""
    a = abs(value)
    if a >= 100:
        return f"{value:.2f}"
    if a >= 1:
        return f"{value:.3f}"
    if a >= 0.01:
        return f"{value:.4f}"
    return f"{value:.2e}"


def format_plot_segment_tooltip(seg: dict, unit: str = "") -> str:
    """Hover text for a contribution-tree plot segment."""
    unit = unit or seg.get("unit") or ""
    lines = []
    if seg.get("is_aggregate"):
        field = seg.get("aggregate_by", "")
        label = PLOT_AGGREGATE_LABELS.get(field, field)
        if label and seg.get("aggregate_key"):
            lines.append(f"{label}: {seg['aggregate_key']}")
        n = len(seg.get("constituent_uids") or [])
        if n:
            lines.append(f"Processes: {n}")
        products = seg.get("constituent_products") or []
        for name in products[:5]:
            lines.append(f"• {name}")
        if len(products) > 5:
            lines.append(f"… and {len(products) - 5} more")
    else:
        if seg.get("product"):
            lines.append(f"Product: {seg['product']}")
        if seg.get("process"):
            lines.append(f"Process: {seg['process']}")
        if seg.get("location"):
            lines.append(f"Location: {seg['location']}")
        if seg.get("database"):
            lines.append(f"Database: {seg['database']}")
    lines.append(f"Tier: {seg['tier']}")
    lines.append(
        f"Path impact: {seg['cumulative_pct']:.2f}% "
        f"({format_impact_abs(seg['cumulative_score'])} {unit})".rstrip()
    )
    lines.append(
        f"Direct impact: {seg['direct_pct']:.2f}% "
        f"({format_impact_abs(seg['direct_emissions_score'])} {unit})".rstrip()
    )
    return "\n".join(lines)


def _json_safe(value):
    """Convert numpy/pandas scalars and nested containers to JSON types."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _json_safe(item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0.0
        return float(value)
    return value


def _segment_label(seg: dict) -> str:
    if seg.get("is_aggregate") and seg.get("aggregate_key"):
        return str(seg["aggregate_key"])
    return str(seg.get("product") or "").strip()


def d3_plot_payload(
    segments: list[dict],
    mode: str,
    unit: str = "",
    *,
    empty_message: str = "",
    style: dict | None = None,
    plot_depth: int | None = None,
    color_by: str = "direct",
) -> dict:
    """JSON-ready plot payload: partition geometry plus click ids.

    Geometry (``tier``, ``x0``, ``x1``) is copied, not recomputed. Partition
    plots map those spans onto SVG. Treemap nests the same segments by span
    containment and sizes cells by path-impact span.
    """
    if mode not in D3_PLOT_MODES:
        mode = "icicle"
    if color_by not in GRAPH_COLOR_BY:
        color_by = "direct"
    out_segments: list[dict] = []
    max_tier = 0
    for seg in segments:
        item = {}
        for field in _D3_SEGMENT_FIELDS:
            if field in seg:
                item[field] = _json_safe(seg[field])
        item.setdefault("toggle_uid", item["unique_id"])
        item["click_uid"] = plot_click_target_uid(item)
        item["label"] = _segment_label(seg)
        item["tooltip"] = format_plot_segment_tooltip(seg, unit)
        direct_pct = float(item.get("direct_pct") or 0.0)
        item["direct_sign"] = _impact_sign(direct_pct)
        item["color_key"] = _graph_color_key(
            {
                "product": item.get("product") or "",
                "name": item.get("process") or "",
                "location": item.get("location") or "",
                "database": item.get("database") or "",
            },
            color_by,
        )
        max_tier = max(max_tier, int(item.get("tier") or 0))
        out_segments.append(item)
    computed_depth = max(1, max_tier + 1) if out_segments else 1
    return {
        "mode": mode,
        "kind": "partition",
        "unit": unit or "",
        "empty_message": empty_message,
        "style": dict(style or {}),
        "plot_depth": int(plot_depth) if plot_depth is not None else computed_depth,
        # D3 log-scale high is always 100% of the total score (not the visible max).
        "max_direct_pct": 100.0,
        "color_by": color_by,
        "segments": out_segments,
    }


GRAPH_COLOR_BY = ("direct", "product", "process", "location", "database")
GRAPH_EDGE_MAX_WIDTH = 40
_GRAPH_AGGREGATE_ID_BASE = 10_000


def _graph_node_css_class(name: str, *, is_demand: bool) -> str:
    """Sankey box stroke class from the process name (no Brightway lookup)."""
    if is_demand:
        return "demand"
    lowered = (name or "").lower()
    if "treatment of" in lowered:
        return "treatment"
    if "market for" in lowered:
        return "market"
    if "market group" in lowered:
        return "marketgroup"
    return "production"


def _impact_sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _graph_color_key(meta: dict, color_by: str) -> str:
    if color_by == "product":
        return str(meta.get("product") or "").strip()
    if color_by == "process":
        return str(meta.get("name") or "").strip()
    if color_by == "location":
        return str(meta.get("location") or "").strip()
    if color_by == "database":
        return str(meta.get("database") or "").strip()
    return ""


def _graph_meta(node, metadata_lookup: Callable[[int], dict] | None) -> dict:
    if metadata_lookup is None:
        return {}
    return metadata_lookup(getattr(node, "activity_datapackage_id", None)) or {}


def _descendant_uids(pcm: dict[NodeId, list[NodeId]], start: NodeId) -> set[NodeId]:
    out: set[NodeId] = set()
    queue = list(pcm.get(start, []))
    while queue:
        uid = queue.pop()
        if uid in out:
            continue
        out.add(uid)
        queue.extend(pcm.get(uid, []))
    return out


def format_graph_node_tooltip(node: dict, unit: str = "") -> str:
    """Hover text for a tree-plot / Sankey-plot process box."""
    lines = []
    if node.get("is_aggregate") and node.get("aggregate_key"):
        field = node.get("aggregate_by", "")
        label = PLOT_AGGREGATE_LABELS.get(field, field)
        if label:
            lines.append(f"{label}: {node['aggregate_key']}")
        n = len(node.get("constituent_uids") or [])
        if n:
            lines.append(f"Processes: {n}")
    else:
        if node.get("product"):
            lines.append(f"Product: {node['product']}")
        if node.get("name"):
            lines.append(f"Process: {node['name']}")
        loc = str(node.get("location") or "").strip()
        if loc:
            lines.append(f"Location: {loc}")
        if node.get("database"):
            lines.append(f"Database: {node['database']}")
    lines.append(
        f"Path impact: {node['path_pct']:.2f}% "
        f"({format_impact_abs(node['cumulative_score'])} {unit})".rstrip()
    )
    lines.append(
        f"Direct impact: {node['direct_pct']:.2f}% "
        f"({format_impact_abs(node['direct_emissions_score'])} {unit})".rstrip()
    )
    return "\n".join(lines)


def format_graph_edge_tooltip(edge: dict) -> str:
    """Hover text for a tree-plot / Sankey-plot ribbon (fallback if JS is absent)."""
    lines = []
    product = str(edge.get("product") or "").strip()
    if product:
        lines.append(f"Product: {product}")
    amount = edge.get("amount")
    if amount is not None:
        try:
            amt = float(amount)
        except (TypeError, ValueError):
            amt = None
        if amt is not None:
            flow_unit = str(edge.get("amount_unit") or "").strip()
            lines.append(
                f"Flow amount: {format_impact_abs(amt)}"
                + (f" {flow_unit}" if flow_unit else "")
            )
    path_pct = edge.get("impact_pct_total")
    cum = edge.get("impact_cumulative")
    if path_pct is not None and cum is not None:
        iunit = str(edge.get("impact_unit") or "").strip()
        lines.append(
            f"Path impact: {float(path_pct):.2f}% "
            f"({format_impact_abs(float(cum))}"
            f"{(' ' + iunit) if iunit else ''})".rstrip()
        )
    return "\n".join(lines)


def sankey_traversal_max_depth(mode: str | None, value: float | int) -> int | None:
    """NNEV ``max_depth`` for a Sankey Adjust policy.

    ``None`` means unlimited (path / cumulative). Tier mode adds two hops
    past the displayed tier: NNEV counts the virtual root as depth 0, and
    the extra hop lets a two-process cycle remap both flows onto unique
    process boxes. Startup at tier 1 therefore uses depth 3, not 1000 visits.
    """
    if (mode or "tier") != "tier":
        return None
    return max(1, int(value) + 2)


def merge_graph_edges(edges: list[dict]) -> list[dict]:
    """One ribbon per process pair: keep the largest path impact, drop cutoff tails."""
    best: dict[tuple[int, int], dict] = {}
    for rec in edges:
        pair = (int(rec["source_id"]), int(rec["target_id"]))
        prev = best.get(pair)
        if prev is None:
            best[pair] = rec
            continue
        if abs(float(rec.get("impact_cumulative") or 0.0)) > abs(
            float(prev.get("impact_cumulative") or 0.0)
        ):
            best[pair] = rec
    return list(best.values())


def overlay_inventory_directs(payload: dict, lca, total_score: float) -> None:
    """Replace visit-level directs with solved-inventory directs (unique-process Sankey)."""
    from activity_browser.bwutils.lca_inputs import activity_direct_impacts

    directs = activity_direct_impacts(lca)
    if not directs:
        return
    unit = payload.get("unit") or ""
    for rec in payload.get("nodes") or []:
        if rec.get("is_aggregate"):
            continue
        aid = rec.get("activity_id")
        if aid not in directs:
            continue
        direct = float(directs[aid])
        rec["direct_emissions_score"] = direct
        rec["direct_pct"] = (direct / total_score) * 100.0 if total_score else 0.0
        rec["direct_emissions_score_normalized"] = (
            direct / total_score if total_score else 0.0
        )
        rec["direct_sign"] = _impact_sign(direct)
        rec["tooltip"] = format_graph_node_tooltip(rec, unit)


def inventory_direct_lookup(
    nodes: dict,
    directs: dict[int, float],
) -> Callable[[NodeId], float]:
    """Map a visit uid to the solved-inventory direct of its unique process."""

    def lookup(uid: NodeId) -> float:
        node = nodes.get(uid)
        aid = _activity_id(node)
        if aid is not None and aid in directs:
            return float(directs[aid])
        if node is None:
            return 0.0
        return float(getattr(node, "direct_emissions_score", 0.0) or 0.0)

    return lookup


def mapped_edge_amounts(nodes: dict, edges: list, payload_nodes: list[dict]) -> dict[tuple[int, int], float]:
    """Sum NNEV exchange amounts onto unique-process (source, target) pairs."""
    uid_by_act: dict[int, int] = {}
    drawn = {int(n["id"]) for n in payload_nodes if not n.get("is_aggregate")}
    for rec in payload_nodes:
        aid = rec.get("activity_id")
        if aid is not None and not rec.get("is_aggregate"):
            uid_by_act[int(aid)] = int(rec["id"])

    def mapped(uid: int) -> int:
        if uid in drawn:
            return uid
        node = nodes.get(uid)
        aid = _activity_id(node)
        if aid is not None and aid in uid_by_act:
            return uid_by_act[aid]
        return uid

    amounts: dict[tuple[int, int], float] = defaultdict(float)
    for edge in edges:
        src = mapped(int(edge.producer_unique_id))
        tgt = mapped(int(edge.consumer_unique_id))
        if src == tgt or src not in drawn or tgt not in drawn:
            continue
        amounts[(src, tgt)] += float(getattr(edge, "amount", 0.0) or 0.0)
    return amounts


def d3_graph_payload(
    nodes: dict,
    edges: list,
    total_score: float,
    *,
    root_uid: NodeId,
    included_uids: set[NodeId] | None = None,
    metadata_lookup: Callable[[int], dict] | None = None,
    aggregate_by: str | None = None,
    color_by: str = "direct",
    unit: str = "",
    empty_message: str = "",
    style: dict | None = None,
    visited: set | None = None,
    unique_activities: bool = False,
    opened_uids: set | None = None,
) -> dict:
    """JSON-ready node-link payload for the shared tree/Sankey renderer.

    Only ``included_uids`` (the display set) become boxes. The virtual demand
    root is omitted. JS must not recompute adjust policy or click targets.
    ``unique_activities`` (Sankey) keeps one box per process (the highest-path
    visit) and remaps later-visit edges onto that box so circular supply stays
    two processes.
    """
    if color_by not in GRAPH_COLOR_BY:
        color_by = "direct"
    visited_set = set(visited) if visited is not None else set(nodes)
    opened_set = set(opened_uids) if opened_uids is not None else visited_set
    pcm = build_parent_child_map(nodes, edges)

    def is_included(uid: NodeId) -> bool:
        if uid == root_uid:
            return False
        if included_uids is None:
            return uid in nodes
        return uid in included_uids and uid in nodes

    drawn: set[NodeId] = {uid for uid in nodes if is_included(uid)}
    if unique_activities:
        drawn = keep_best_visit_per_activity(nodes, edges, drawn, root_uid)
    skip: set[NodeId] = set()
    aggregate_nodes: list[dict] = []
    demand_uids = set(pcm.get(root_uid, []))

    if aggregate_by and drawn:
        parents = {root_uid} | drawn
        agg_index = 0
        for parent_uid in parents:
            kids = [
                uid
                for uid in pcm.get(parent_uid, [])
                if uid in drawn and uid not in skip
            ]
            groups: dict[str, list[NodeId]] = defaultdict(list)
            for uid in kids:
                meta = _graph_meta(nodes[uid], metadata_lookup)
                meta_row = {
                    "product": meta.get("product", ""),
                    "process": meta.get("name", ""),
                    "location": meta.get("location", ""),
                    "unit": meta.get("unit", ""),
                    "database": meta.get("database", ""),
                }
                groups[_aggregate_field_value(meta_row, aggregate_by)].append(uid)
            for key, group in groups.items():
                if len(group) <= 1:
                    continue
                agg_id = -(_GRAPH_AGGREGATE_ID_BASE + agg_index)
                agg_index += 1
                group_nodes = [nodes[uid] for uid in group]
                cum = sum(n.cumulative_score for n in group_nodes)
                direct = sum(n.direct_emissions_score for n in group_nodes)
                path_pct = (cum / total_score) * 100.0 if total_score else 0.0
                direct_pct = (direct / total_score) * 100.0 if total_score else 0.0
                rec = {
                    "id": agg_id,
                    "visit_id": agg_id,
                    "click_uid": parent_uid,
                    "toggle_uid": parent_uid,
                    "is_aggregate": True,
                    "is_terminal": True,
                    "has_hidden_suppliers": False,
                    "can_collapse": False,
                    "name": key,
                    "location": "",
                    "product": "",
                    "database": "",
                    "class": "production",
                    "direct_sign": _impact_sign(direct),
                    "direct_pct": float(direct_pct),
                    "direct_emissions_score_normalized": (
                        float(direct / total_score) if total_score else 0.0
                    ),
                    "path_pct": float(path_pct),
                    "cumulative_score": float(cum),
                    "direct_emissions_score": float(direct),
                    "color_key": key if color_by != "direct" else "",
                    "aggregate_key": key,
                    "aggregate_by": aggregate_by,
                    "constituent_uids": list(group),
                    "parent_id": parent_uid,
                }
                rec["tooltip"] = format_graph_node_tooltip(rec, unit)
                aggregate_nodes.append(rec)
                for uid in group:
                    skip.add(uid)
                    skip |= _descendant_uids(pcm, uid)

    drawn -= skip
    drawn_acts = {
        _activity_id(nodes[uid])
        for uid in drawn
        if _activity_id(nodes.get(uid)) is not None
    }

    def _represents_drawn_activity(child: NodeId) -> bool:
        if not unique_activities:
            return False
        aid = _activity_id(nodes.get(child))
        return aid is not None and aid in drawn_acts

    out_nodes: list[dict] = []
    for uid in sorted(drawn):
        node = nodes[uid]
        meta = _graph_meta(node, metadata_lookup)
        loc = str(meta.get("location") or "").strip()
        name = str(meta.get("name") or "").strip()
        product = str(meta.get("product") or "").strip()
        database = str(meta.get("database") or "").strip()
        cum = float(node.cumulative_score)
        direct = float(node.direct_emissions_score)
        path_pct = (cum / total_score) * 100.0 if total_score else 0.0
        direct_pct = (direct / total_score) * 100.0 if total_score else 0.0
        rem = max(abs(cum) - abs(direct), 0.0)
        child_ids = supplier_visit_ids(
            pcm, nodes, uid, unique_activities=unique_activities
        )
        opened = uid in opened_set
        hidden = any(
            child not in drawn
            and child not in skip
            and not _represents_drawn_activity(child)
            for child in child_ids
        )
        unopened_expand = (not opened) and rem > 0
        if unique_activities and unopened_same_activity_hops(nodes, uid, opened_set):
            unopened_expand = True
        ancestors = (
            _display_ancestors(pcm, root_uid, uid, drawn) if unique_activities else set()
        )
        exclusive_shown: list[NodeId] = []
        for cid in child_ids:
            if unique_activities:
                if cid not in drawn and not _represents_drawn_activity(cid):
                    continue
                aid = _activity_id(nodes.get(cid))
                first = cid if cid in drawn else next(
                    (u for u in drawn if _activity_id(nodes.get(u)) == aid),
                    None,
                )
                if (
                    first is not None
                    and first not in ancestors
                    and first != uid
                    and first not in exclusive_shown
                ):
                    exclusive_shown.append(first)
            elif cid in drawn:
                exclusive_shown.append(cid)
        can_collapse = bool(exclusive_shown)
        expand = hidden or unopened_expand
        terminal = opened and not expand and not can_collapse
        rec = {
            "id": int(uid),
            "visit_id": int(uid),
            "click_uid": int(uid),
            "toggle_uid": int(uid),
            "is_aggregate": False,
            "is_terminal": bool(terminal),
            "has_hidden_suppliers": bool(expand),
            "can_collapse": can_collapse,
            "name": name,
            "location": loc,
            "product": product,
            "database": database,
            "code": str(meta.get("code") or "").strip(),
            "class": _graph_node_css_class(name, is_demand=uid in demand_uids),
            "direct_sign": _impact_sign(direct),
            "direct_pct": float(direct_pct),
            "direct_emissions_score_normalized": (
                float(direct / total_score) if total_score else 0.0
            ),
            "path_pct": float(path_pct),
            "cumulative_score": cum,
            "direct_emissions_score": direct,
            "color_key": _graph_color_key(
                {"product": product, "name": name, "location": loc, "database": database},
                color_by,
            ),
        }
        aid = _activity_id(node)
        if aid is not None:
            rec["activity_id"] = int(aid)
        rec["tooltip"] = format_graph_node_tooltip(rec, unit)
        out_nodes.append(rec)

    out_nodes.extend(aggregate_nodes)
    drawn_ids = {n["id"] for n in out_nodes}
    aid_to_uid: dict[int, NodeId] = {}
    if unique_activities:
        for uid in sorted(drawn):
            aid = _activity_id(nodes.get(uid))
            if aid is not None and aid not in aid_to_uid:
                aid_to_uid[aid] = uid

    def _map_visit(uid: NodeId) -> NodeId:
        if uid in drawn:
            return uid
        aid = _activity_id(nodes.get(uid))
        if unique_activities and aid is not None and aid in aid_to_uid:
            return aid_to_uid[aid]
        return uid

    out_edges: list[dict] = []
    for edge in edges:
        orig_src = edge.producer_unique_id
        orig_tgt = edge.consumer_unique_id
        if orig_src in skip or orig_tgt in skip:
            continue
        src, tgt = orig_src, orig_tgt
        if unique_activities:
            src = _map_visit(orig_src)
            tgt = _map_visit(orig_tgt)
            if src == tgt:
                continue
        if src not in drawn_ids or tgt not in drawn_ids:
            continue
        producer = nodes.get(orig_src)
        if producer is None:
            continue
        cum = float(producer.cumulative_score)
        path_pct = (cum / total_score) * 100.0 if total_score else 0.0
        meta = _graph_meta(producer, metadata_lookup)
        product = str(meta.get("product") or "").strip()
        rec = {
            "source_id": int(src),
            "target_id": int(tgt),
            "producer_unique_id": int(orig_src),
            "consumer_unique_id": int(orig_tgt),
            "weight": abs(cum / total_score) * GRAPH_EDGE_MAX_WIDTH if total_score else 0.0,
            "path_sign": _impact_sign(cum),
            "class": "benefit" if _impact_sign(cum) < 0 else "impact",
            "product": product,
            "impact_cumulative": cum,
            "impact_pct_total": float(path_pct),
            "impact_unit": unit or "",
            "amount": float(getattr(producer, "supply_amount", 0.0) or 0.0),
            "amount_unit": str(meta.get("unit") or "").strip(),
        }
        rec["tooltip"] = format_graph_edge_tooltip(rec)
        out_edges.append(rec)

    for agg in aggregate_nodes:
        parent_uid = agg["parent_id"]
        if parent_uid == root_uid or parent_uid not in drawn_ids:
            continue
        cum = float(agg["cumulative_score"])
        path_pct = float(agg["path_pct"])
        rec = {
            "source_id": int(agg["id"]),
            "target_id": int(parent_uid),
            "weight": abs(cum / total_score) * GRAPH_EDGE_MAX_WIDTH if total_score else 0.0,
            "path_sign": _impact_sign(cum),
            "class": "benefit" if _impact_sign(cum) < 0 else "impact",
            "product": str(agg.get("aggregate_key") or ""),
            "impact_cumulative": cum,
            "impact_pct_total": path_pct,
            "impact_unit": unit or "",
        }
        rec["tooltip"] = format_graph_edge_tooltip(rec)
        out_edges.append(rec)

    payload = {
        "kind": "graph",
        "unit": unit or "",
        "empty_message": empty_message if not out_nodes else "",
        "style": dict(style or {}),
        "color_by": color_by,
        "nodes": [_json_safe(n) for n in out_nodes],
        "edges": [_json_safe(e) for e in (
            merge_graph_edges(out_edges) if unique_activities else out_edges
        )],
    }
    return payload


def is_terminal_node(
    nodes: dict,
    edges: list,
    visited: set,
    uid: NodeId,
) -> bool:
    """True when a visited node has no downstream suppliers in the graph."""
    if uid not in visited:
        return False
    pcm = build_parent_child_map(nodes, edges)
    return not pcm.get(uid)


def _aggregate_field_value(segment: dict, field: str) -> str:
    if field == "product":
        raw = segment.get("product")
    elif field == "name":
        raw = segment.get("process")
    elif field == "location":
        raw = segment.get("location")
    elif field == "unit":
        raw = segment.get("unit")
    elif field == "database":
        raw = segment.get("database")
    else:
        raw = ""
    text = str(raw or "").strip()
    return text or "(unknown)"


def _segment_with_toggle(segment: dict) -> dict:
    out = dict(segment)
    out.setdefault("is_aggregate", False)
    out.setdefault("toggle_uid", segment["unique_id"])
    return out


def _parent_plot_span(
    parent_uid: NodeId,
    segments_by_uid: dict[int, dict],
    root_uid: NodeId,
) -> tuple[float, float]:
    if parent_uid == root_uid:
        return 0.0, 1.0
    parent = segments_by_uid.get(parent_uid)
    if parent is None:
        return 0.0, 1.0
    return parent["x0"], parent["x1"]


def _merge_sibling_segments(
    children: list[dict],
    aggregate_by: str,
    px0: float,
    px1: float,
    total_score: float,
    parent_uid: NodeId,
    segments_by_uid: dict[int, dict],
    root_uid: NodeId,
) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for child in children:
        groups[_aggregate_field_value(child, aggregate_by)].append(child)

    ordered = sorted(
        groups.items(),
        key=lambda pair: sum(abs(s["cumulative_score"]) for s in pair[1]),
        reverse=True,
    )
    span = px1 - px0
    if parent_uid == root_uid:
        layout_span = span
    else:
        parent_seg = segments_by_uid.get(parent_uid)
        if parent_seg is None:
            layout_span = span
        else:
            layout_span = _upstream_layout_span(
                span,
                parent_seg["cumulative_score"],
                parent_seg["direct_emissions_score"],
            )
    total_mag = sum(sum(abs(s["cumulative_score"]) for s in grp) for _, grp in ordered)
    x = px0
    merged: list[dict] = []
    for key, group in ordered:
        group_cum = sum(s["cumulative_score"] for s in group)
        group_direct = sum(s["direct_emissions_score"] for s in group)
        group_mag = sum(abs(s["cumulative_score"]) for s in group)
        share = group_mag / total_mag if total_mag else 0.0
        width = share * layout_span
        constituent_uids = [s["unique_id"] for s in group]
        is_aggregate = len(group) > 1
        if is_aggregate:
            base = dict(group[0])
            base.update({
                "is_aggregate": True,
                "toggle_uid": parent_uid,
                "parent_unique_id": parent_uid,
                "constituent_uids": constituent_uids,
                "aggregate_key": key,
                "aggregate_by": aggregate_by,
            })
        else:
            base = _segment_with_toggle(group[0])
        base["x0"] = x
        base["x1"] = x + width
        base["cumulative_score"] = group_cum
        base["direct_emissions_score"] = group_direct
        base["cumulative_pct"] = (
            (group_cum / total_score) * 100.0 if total_score else 0.0
        )
        base["direct_pct"] = (
            (group_direct / total_score) * 100.0 if total_score else 0.0
        )
        base["constituent_products"] = [
            s.get("product", "") for s in group if s.get("product")
        ]
        merged.append(base)
        x += width
    return merged


def aggregate_plot_segments(
    segments: list[dict],
    aggregate_by: str | None,
    pcm: dict[NodeId, list[NodeId]],
    root_uid: NodeId,
    total_score: float,
) -> list[dict]:
    """Merge sibling plot segments under each parent by a metadata field."""
    if not segments:
        return []
    if not aggregate_by:
        return [_segment_with_toggle(s) for s in segments]

    child_to_parent = {
        child: parent for parent, kids in pcm.items() for child in kids
    }
    segments_by_uid = {s["unique_id"]: dict(s) for s in segments}
    max_tier = max(s["tier"] for s in segments)
    merged_by_tier: dict[int, list[dict]] = {}

    for tier in range(max_tier + 1):
        tier_children = [dict(s) for s in segments if s["tier"] == tier]
        by_parent: dict[NodeId, list[dict]] = defaultdict(list)
        for seg in tier_children:
            parent_uid = child_to_parent.get(seg["unique_id"], root_uid)
            by_parent[parent_uid].append(seg)

        tier_merged: list[dict] = []
        for parent_uid, children in by_parent.items():
            px0, px1 = _parent_plot_span(parent_uid, segments_by_uid, root_uid)
            tier_merged.extend(
                _merge_sibling_segments(
                    children,
                    aggregate_by,
                    px0,
                    px1,
                    total_score,
                    parent_uid,
                    segments_by_uid,
                    root_uid,
                )
            )
        merged_by_tier[tier] = tier_merged
        for seg in tier_merged:
            if not seg.get("is_aggregate"):
                segments_by_uid[seg["unique_id"]] = seg

    out: list[dict] = []
    for tier in range(max_tier + 1):
        out.extend(merged_by_tier.get(tier, []))
    return out


def build_plot_segments(
    nodes: dict,
    edges: list,
    total_score: float,
    max_depth: int,
    root_uid: NodeId | None = None,
    metadata_lookup: Callable[[int], dict] | None = None,
    included_uids: set[NodeId] | None = None,
    aggregate_by: str | None = None,
) -> list[dict]:
    """Chain layout plus optional sibling aggregation for contribution-tree plots."""
    segments = build_chain_layout(
        nodes,
        edges,
        total_score,
        max_depth=max_depth,
        root_uid=root_uid,
        metadata_lookup=metadata_lookup,
        included_uids=included_uids,
    )
    if not segments:
        return []
    if root_uid is None:
        roots = [n for n in nodes.values() if getattr(n, "depth", None) == 0]
        if len(roots) != 1:
            return segments
        root_uid = roots[0].unique_id
    pcm = build_parent_child_map(nodes, edges)
    return aggregate_plot_segments(
        segments, aggregate_by, pcm, root_uid, total_score
    )


# ---------------------------------------------------------------------------
# Sunburst ring builder
# ---------------------------------------------------------------------------

def build_sunburst_rings(
    nodes: dict,
    edges: list,
    total_score: float,
    max_depth: int,
    root_uid: NodeId | None = None,
) -> list[list[dict]]:
    """Build per-tier ring data for a sunburst (layered donut) chart.

    Rings use **display tiers** (RF = 0), not Brightway's mutable ``node.depth``.
    ``max_depth`` is the number of rings (tiers ``0 .. max_depth-1``).

    Each ring is a list of wedge dicts with ``unique_id``, ``label``, ``share``,
    ``cumulative_score``, ``parent_unique_id``.
    """
    if not nodes or total_score == 0.0:
        return []

    if root_uid is None:
        roots = [n for n in nodes.values() if getattr(n, "depth", None) == 0]
        if len(roots) != 1:
            return []
        root_uid = roots[0].unique_id

    tiers = compute_node_tiers(nodes, edges, root_uid)
    by_tier: dict[int, list] = {}
    for node in nodes.values():
        if node.unique_id == root_uid:
            continue
        t = tiers.get(node.unique_id)
        if t is not None and 0 <= t < max_depth:
            by_tier.setdefault(t, []).append(node)

    rings: list[list[dict]] = []
    for tier in range(0, max_depth):
        depth_nodes = by_tier.get(tier, [])
        if not depth_nodes:
            break

        by_parent: dict[NodeId, list] = {}
        for node in depth_nodes:
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

            children.sort(key=lambda c: abs(c.cumulative_score), reverse=True)
            for child in children:
                share = (
                    abs(child.cumulative_score) / abs(parent_score)
                    if parent_score
                    else 0.0
                )
                ring.append({
                    "unique_id": child.unique_id,
                    "label": getattr(child, "_label", str(child.unique_id)),
                    "share": share,
                    "cumulative_score": child.cumulative_score,
                    "parent_unique_id": parent_id,
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
