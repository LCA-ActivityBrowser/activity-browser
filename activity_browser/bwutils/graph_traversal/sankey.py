"""Unique-process Sankey helpers (one box per process).

Wraps visit-based ``engine`` display-set / Adjust / node-link payload.
Must not import ``tree`` or ``partition_plots``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from activity_browser.bwutils.graph_traversal.engine import (
    NodeId,
    _activity_id,
    _descendant_uids,
    _graph_color_key,
    _graph_meta,
    _graph_node_css_class,
    _impact_sign,
    _json_safe,
    _aggregate_field_value,
    GRAPH_COLOR_BY,
    GRAPH_EDGE_MAX_WIDTH,
    _GRAPH_AGGREGATE_ID_BASE,
    build_parent_child_map,
    compute_node_tiers,
    coverage_of_uids,
    format_graph_edge_tooltip,
    format_graph_node_tooltip,
)
from activity_browser.bwutils.graph_traversal import engine as _engine


def run_expand_policy(
    state,
    *,
    mode: str,
    value: float,
    total_score: float,
    on_progress=None,
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> tuple[set[NodeId] | None, set[NodeId] | None]:
    """Traverse with unique-process eligibility; collapse the display set after."""
    root_uid = state._root_node.unique_id

    def eligible() -> set[NodeId] | None:
        return keep_best_visit_per_activity(
            state.nodes,
            state.edges,
            {uid for uid in state.nodes if uid != root_uid},
            root_uid,
        )

    included, to_expand = _engine.run_expand_policy(
        state,
        mode=mode,
        value=value,
        total_score=total_score,
        on_progress=on_progress,
        direct_lookup=direct_lookup,
        eligible_ids=eligible,
    )
    if included is not None:
        included = keep_best_visit_per_activity(
            state.nodes, state.edges, included, root_uid
        )
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
    direct_lookup: Callable[[NodeId], float] | None = None,
) -> tuple[set[NodeId], set[NodeId]]:
    """Visit display set, then one box per process (highest |path impact|)."""
    eligible = None
    if mode == "cumulative":
        eligible = keep_best_visit_per_activity(
            nodes,
            edges,
            {uid for uid in nodes if uid != root_uid},
            root_uid,
        )
    included, to_expand = _engine.graph_display_set(
        nodes,
        edges,
        mode=mode,
        value=value,
        total_score=total_score,
        root_uid=root_uid,
        visited=visited,
        direct_lookup=direct_lookup,
        eligible_ids=eligible,
    )
    included = keep_best_visit_per_activity(nodes, edges, included, root_uid)
    return included, to_expand


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
) -> list[NodeId]:
    """Supplier visit ids of every NNEV visit of the same process as ``uid``."""
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
    root_uid: NodeId | None = None,
) -> set[NodeId]:
    """Expand or collapse one visit in a calculated graph display set.

    Manual expand shows every unique-process supplier already in the calculated
    graph (engine cutoff). Adjust-hidden siblings come back on expand.
    Collapse runs only when those suppliers are already shown. Already-drawn
    processes stay one box (no cycle unroll).
    """
    unique_activities = True
    pcm = build_parent_child_map(nodes, edges)
    children = supplier_visit_ids(pcm, nodes, uid)
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
    unique_activities = True
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
        for cid in supplier_visit_ids(pcm, nodes, uid)
        if _activity_id(nodes.get(cid)) not in drawn_acts
    ]
    return set(included) | set(to_add)

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
    opened_uids: set | None = None,
) -> dict:
    """JSON-ready node-link payload for the shared tree/Sankey renderer.

    Only ``included_uids`` (the display set) become boxes. The virtual demand
    root is omitted. JS must not recompute adjust policy or click targets.
    ``unique_activities`` (Sankey) keeps one box per process (the highest-path
    visit) and remaps later-visit edges onto that box so circular supply stays
    two processes.
    """
    unique_activities = True
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
        child_ids = supplier_visit_ids(pcm, nodes, uid)
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
