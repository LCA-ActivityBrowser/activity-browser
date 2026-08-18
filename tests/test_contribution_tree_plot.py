"""Tests for Contribution Tree plot constants and D3 theme helpers (no Qt widgets)."""

from activity_browser.app.pages.lca_results.contribution_tree_d3_plot import (
    partition_segment_edge_color,
)
from activity_browser.app.pages.lca_results.contribution_tree_plot import (
    PLOT_GRAPH,
    PLOT_ICICLE,
    PLOT_MODES,
    PLOT_SUNBURST,
    PLOT_TIER_BARS,
    PLOT_TREEMAP,
)


def test_plot_modes_are_d3_only():
    ids = [mode_id for mode_id, _label in PLOT_MODES]
    assert ids[0] == PLOT_GRAPH
    assert ids[1] == PLOT_ICICLE
    assert ids[2] == PLOT_TIER_BARS
    assert ids == [
        PLOT_GRAPH,
        PLOT_ICICLE,
        PLOT_TIER_BARS,
        PLOT_SUNBURST,
        PLOT_TREEMAP,
    ]


def test_partition_segment_edge_contrasts_in_both_themes():
    light = partition_segment_edge_color(dark=False)
    dark = partition_segment_edge_color(dark=True)
    assert light.lower() not in {"#fff", "#ffffff", "white"}
    assert dark.lower() not in {"#fff", "#ffffff", "white"}
    assert light != dark
