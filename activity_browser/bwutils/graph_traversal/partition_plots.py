"""Partition-plot helpers: horizontal/vertical chain, sunburst, treemap/icicle.

May import ``engine``. Must not import ``sankey``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from activity_browser.bwutils.graph_traversal.engine import (
    GRAPH_COLOR_BY,
    NodeId,
    PLOT_AGGREGATE_LABELS,
    _aggregate_field_value,
    _find_parent,
    _graph_color_key,
    _impact_sign,
    _json_safe,
    build_parent_child_map,
    compute_node_tiers,
    cumulative_percent,
    direct_percent,
    format_impact_abs,
)

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
