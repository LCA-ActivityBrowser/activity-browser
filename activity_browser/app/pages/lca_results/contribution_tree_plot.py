"""Sunburst plot for the Contribution Tree tab."""

from __future__ import annotations

from typing import Optional

from bw_graph_tools.graph_traversal import SameNodeEachVisitGraphTraversal

from activity_browser.bwutils.contribution_tree import build_sunburst_rings
from activity_browser.ui import widgets

class SunburstPlot(widgets.ABPlot):
    """Layered donut chart showing the contribution tree by tier.

    Ring construction: one ring per tier (depth 1…plot_depth).  Each wedge's
    angular width = child.cumulative_score / parent.cumulative_score.  An
    "other" wedge fills the remainder where the traversal was pruned.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Contribution Tree"
        self._state: Optional[SameNodeEachVisitGraphTraversal] = None
        self._total_score: float = 0.0
        self._plot_depth: int = 3

    def set_state(
        self,
        state: SameNodeEachVisitGraphTraversal,
        total_score: float,
        plot_depth: int = 3,
    ) -> None:
        self._state = state
        self._total_score = total_score
        self._plot_depth = plot_depth
        self.plot()

    def update_depth(self, plot_depth: int) -> None:
        self._plot_depth = plot_depth
        self.plot()

    def plot(self) -> None:
        if self._state is None or self._total_score == 0.0:
            self.figure.clear()
            self.canvas.draw_idle()
            return

        rings = build_sunburst_rings(
            self._state.nodes,
            self._state.edges,
            self._total_score,
            max_depth=self._plot_depth,
        )
        if not rings:
            self.figure.clear()
            self.canvas.draw_idle()
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111, polar=True)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_axis_off()

        n_rings = len(rings)
        ring_width = 1.0 / (n_rings + 1)  # leave space for centre label

        import numpy as np
        import matplotlib

        cmap = matplotlib.colormaps["tab20c"]

        for ring_idx, ring in enumerate(rings):
            bottom = ring_width * (ring_idx + 1)

            # Track angular position for each parent
            # We need to lay out wedges respecting parent arc positions.
            # Build per-parent wedge lists
            by_parent: dict = {}
            for w in ring:
                by_parent.setdefault(w["parent_unique_id"], []).append(w)

            # For tier-1 ring: parent is root, arc starts at 0, full circle
            # For deeper rings: use parent wedge start angles (stored per uid)
            if ring_idx == 0:
                parent_starts = {list(by_parent.keys())[0]: 0.0}
                parent_spans = {list(by_parent.keys())[0]: 2 * np.pi}
            else:
                parent_starts = getattr(self, "_wedge_starts", {})
                parent_spans = getattr(self, "_wedge_spans", {})

            new_starts: dict = {}
            new_spans: dict = {}

            for parent_uid, wedges in by_parent.items():
                p_start = parent_starts.get(parent_uid, 0.0)
                p_span = parent_spans.get(parent_uid, 2 * np.pi)

                theta = p_start
                for i, w in enumerate(wedges):
                    arc = w["share"] * p_span
                    colour = (
                        (0.7, 0.7, 0.7, 0.5)
                        if w["is_other"]
                        else cmap((ring_idx * 7 + i) % 20 / 20)
                    )
                    ax.bar(
                        x=theta,
                        width=arc,
                        bottom=bottom,
                        height=ring_width * 0.9,
                        color=colour,
                        edgecolor="white",
                        linewidth=0.5,
                        align="edge",
                    )
                    if not w["is_other"] and arc > 0.2:
                        label = str(w.get("label", ""))[:20]
                        mid = theta + arc / 2
                        ax.text(
                            mid,
                            bottom + ring_width * 0.45,
                            label,
                            ha="center",
                            va="center",
                            fontsize=6,
                            rotation=0,
                            clip_on=True,
                        )
                    new_starts[w["unique_id"]] = theta
                    new_spans[w["unique_id"]] = arc
                    theta += arc

            self._wedge_starts = new_starts
            self._wedge_spans = new_spans

        # Centre label
        ax.text(
            0, 0,
            f"Tier {self._plot_depth}",
            ha="center", va="center",
            fontsize=8,
            transform=ax.transData,
        )

        self.finish_plot()

