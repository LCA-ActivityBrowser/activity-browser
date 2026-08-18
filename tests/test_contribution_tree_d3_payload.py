"""JSON payload for the Contribution Tree D3 preview (no Qt).

Seam: ``d3_plot_payload`` serializes ``build_plot_segments`` output. D3 must
not recompute layout; click ids follow ``plot_click_target_uid``.
"""

from __future__ import annotations

import json

import pytest

from activity_browser.bwutils.contribution_tree import (
    aggregate_plot_segments,
    build_chain_layout,
    build_parent_child_map,
    d3_plot_payload,
    plot_click_target_uid,
)

from tests.test_contribution_tree import _edge, _node, _rf_supplier_tree


def test_d3_plot_payload_keeps_layout_and_is_json_serializable():
    nodes, edges = _rf_supplier_tree()
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    payload = d3_plot_payload(segments, "icicle", unit="kg CO2-Eq")
    dumped = json.dumps(payload)
    loaded = json.loads(dumped)

    assert loaded["mode"] == "icicle"
    assert loaded["unit"] == "kg CO2-Eq"
    assert loaded["color_by"] == "direct"
    assert loaded["max_direct_pct"] == 100.0
    assert len(loaded["segments"]) == len(segments)

    child = next(s for s in loaded["segments"] if s["unique_id"] == 1)
    source = next(s for s in segments if s["unique_id"] == 1)
    assert child["direct_sign"] in (-1, 0, 1)
    assert child["x0"] == pytest.approx(source["x0"])
    assert child["x1"] == pytest.approx(source["x1"])
    assert child["tier"] == source["tier"]
    assert child["click_uid"] == plot_click_target_uid(source)
    assert child["toggle_uid"] == source["unique_id"]
    assert child["activity_id"] == 101
    assert source["activity_id"] == 101


def test_d3_plot_payload_includes_activity_code():
    nodes, edges = _rf_supplier_tree()

    def lookup(aid):
        return {"code": "elec", "database": "ei"} if aid == 101 else {}

    segments = build_chain_layout(
        nodes, edges, 10.0, max_depth=2, root_uid=-1, metadata_lookup=lookup
    )
    payload = d3_plot_payload(segments, "icicle")
    child = next(s for s in payload["segments"] if s["unique_id"] == 1)
    assert child["code"] == "elec"
    assert child["database"] == "ei"


def test_d3_plot_payload_aggregate_click_targets_parent():
    nodes, edges = _rf_supplier_tree()
    pcm = build_parent_child_map(nodes, edges)
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    for seg in segments:
        if seg["tier"] == 1:
            seg["location"] = "CH"
            seg["product"] = f"product-{seg['unique_id']}"
    merged = aggregate_plot_segments(segments, "location", pcm, -1, 10.0)
    payload = d3_plot_payload(merged, "tier_bars", unit="kg")
    band = next(s for s in payload["segments"] if s.get("is_aggregate"))
    assert band["click_uid"] == 0
    assert band["toggle_uid"] == 0
    assert "Path impact:" in band["tooltip"]
    assert "Location: CH" in band["tooltip"] or "CH" in band["tooltip"]


def test_d3_plot_payload_empty_has_message_and_no_segments():
    payload = d3_plot_payload([], "sunburst", empty_message="Use Adjust to explore the supply chain.")
    assert payload["mode"] == "sunburst"
    assert payload["segments"] == []
    assert payload["empty_message"] == "Use Adjust to explore the supply chain."
    json.dumps(payload)


def test_d3_plot_payload_accepts_treemap():
    nodes, edges = _rf_supplier_tree()
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    payload = d3_plot_payload(segments, "treemap")
    assert payload["mode"] == "treemap"
    json.dumps(payload)
    child = next(s for s in payload["segments"] if s["unique_id"] == 1)
    assert child["x0"] == pytest.approx(
        next(s for s in segments if s["unique_id"] == 1)["x0"]
    )


def test_d3_plot_payload_rejects_circle_pack():
    nodes, edges = _rf_supplier_tree()
    segments = build_chain_layout(nodes, edges, 10.0, max_depth=2, root_uid=-1)
    payload = d3_plot_payload(segments, "circle_pack")
    assert payload["mode"] == "icicle"
