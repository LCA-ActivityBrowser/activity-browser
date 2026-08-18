"""Plot-type ids for the Contribution Tree."""

PLOT_SUNBURST = "sunburst"
PLOT_TIER_BARS = "tier_bars"
PLOT_ICICLE = "icicle"
PLOT_TREEMAP = "treemap"
PLOT_GRAPH = "graph"

PLOT_MODES = (
    (PLOT_GRAPH, "Tree"),
    (PLOT_ICICLE, "Horizontal tiers"),
    (PLOT_TIER_BARS, "Vertical tiers"),
    (PLOT_SUNBURST, "Sunburst"),
    (PLOT_TREEMAP, "Treemap"),
)
