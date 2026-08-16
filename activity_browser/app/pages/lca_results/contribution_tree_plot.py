"""Contribution Tree plots — Vertical / Horizontal tiers (sunburst retained, not in UI)."""

from __future__ import annotations

import textwrap
from typing import Callable, Optional

import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.collections import PatchCollection
import numpy as np
from bw_graph_tools.graph_traversal import SameNodeEachVisitGraphTraversal
from matplotlib.patches import Rectangle

from activity_browser.bwutils.contribution_tree import (
    PLOT_AGGREGATE_LABELS,
    build_plot_segments,
    direct_impact_intensity,
)
from activity_browser.ui import widgets

PLOT_SUNBURST = "sunburst"
PLOT_TIER_BARS = "tier_bars"
PLOT_ICICLE = "icicle"

# Sunburst kept in code but hidden from the UI for now.
PLOT_MODES_ALL = (
    (PLOT_SUNBURST, "Sunburst"),
    (PLOT_TIER_BARS, "Vertical tiers"),
    (PLOT_ICICLE, "Horizontal tiers"),
)

PLOT_MODES = (
    (PLOT_TIER_BARS, "Vertical tiers"),
    (PLOT_ICICLE, "Horizontal tiers"),
)

# Re-applied after theme sync (ABPlot otherwise sets edges to axes facecolor).
SEGMENT_EDGE_COLOR = "white"
SEGMENT_EDGE_WIDTH = 0.25

# Match Contribution Tree direct-impact column tint (blue burden / green credit).
_BURDEN_RGB = (70 / 255, 130 / 255, 210 / 255)
_CREDIT_RGB = (85 / 255, 170 / 255, 95 / 255)


def direct_impact_rgba(
    direct_pct: float,
    max_direct_pct: float,
) -> tuple[float, float, float, float]:
    """RGBA for plot segments — blue burdens, green credits."""
    frac = direct_impact_intensity(direct_pct, max_direct_pct)
    alpha = 0.12 + 0.82 * frac
    r, g, b = _CREDIT_RGB if direct_pct < 0 else _BURDEN_RGB
    return (r, g, b, alpha)


class ContributionTreePlot(widgets.ABPlot):
    """Supply-chain plots for the Contribution Tree tab.

    All modes share ``build_chain_layout`` (parent-aligned segments),
    direct-impact colour tinting, product-only labels, and rich hover tooltips.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Contribution Tree"
        self._mode = PLOT_ICICLE
        self._state: Optional[SameNodeEachVisitGraphTraversal] = None
        self._total_score: float = 0.0
        self._plot_depth: int = 3
        self._unit: str = ""
        self._segments: list[dict] = []
        self._max_direct_pct: float = 100.0
        self._hover_targets: list[tuple] = []
        self._included_uids: set[int] | None = None
        self._aggregate_by: str | None = None
        self._on_segment_clicked: Callable[[dict], None] | None = None
        # Hundreds of patches + labels make constrained_layout very slow.
        self.figure.set_layout_engine(None)
        self.show_empty()

    @staticmethod
    def _theme_text_color(*, muted: bool = False) -> str:
        color = plt.rcParams["text.color"]
        if not muted:
            return color
        return mcolors.to_rgba(color, alpha=0.65)

    @staticmethod
    def _is_dark_theme() -> bool:
        face = plt.rcParams["axes.facecolor"]
        if face in ("none", "None"):
            face = plt.rcParams["figure.facecolor"]
        r, g, b = mcolors.to_rgb(face)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 0.45

    def _segment_color(self, direct_pct: float) -> tuple[float, float, float, float]:
        """Segment fill — boosted for readability on dark plot backgrounds."""
        r, g, b, a = direct_impact_rgba(direct_pct, self._max_direct_pct)
        if not self._is_dark_theme():
            return (r, g, b, a)
        intensity = direct_impact_intensity(direct_pct, self._max_direct_pct)
        rgb = np.array([r, g, b], dtype=float)
        target_lum = 0.38 + 0.34 * intensity
        lum = float(rgb @ np.array([0.299, 0.587, 0.114]))
        if lum < target_lum:
            rgb = np.clip(rgb * (target_lum / max(lum, 1e-6)), 0.0, 1.0)
        a = 0.55 + 0.45 * intensity
        return (float(rgb[0]), float(rgb[1]), float(rgb[2]), float(a))

    def _apply_segment_borders(self) -> None:
        for ax in self.figure.axes:
            for patch in ax.patches:
                patch.set_edgecolor(SEGMENT_EDGE_COLOR)
                patch.set_linewidth(SEGMENT_EDGE_WIDTH)
            for coll in ax.collections:
                if isinstance(coll, PatchCollection):
                    coll.set_edgecolor(SEGMENT_EDGE_COLOR)
                    coll.set_linewidth(SEGMENT_EDGE_WIDTH)

    def _sync_plot_to_theme(self) -> None:
        super()._sync_plot_to_theme()
        self._apply_segment_borders()

    def show_empty(self, message: str | None = None) -> None:
        """Blank placeholder — no default matplotlib axes."""
        self._hover_targets = []
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_axis_off()
        if message:
            ax.text(
                0.5,
                0.5,
                message,
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=9,
                color=self._theme_text_color(muted=True),
            )
        self.finish_plot(on_hover=None, on_click=None)

    def set_segment_click_handler(
        self, handler: Callable[[dict], None] | None
    ) -> None:
        """Register tab callback invoked with the clicked segment dict."""
        self._on_segment_clicked = handler

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        if self._state is not None:
            self.plot()

    def set_state(
        self,
        state: SameNodeEachVisitGraphTraversal,
        total_score: float,
        plot_depth: int = 3,
        metadata_lookup: Callable[[int], dict] | None = None,
        unit: str = "",
        included_uids: set[int] | None = None,
        aggregate_by: str | None = None,
    ) -> None:
        self._state = state
        self._total_score = total_score
        self._plot_depth = plot_depth
        self._unit = unit or ""
        self._included_uids = included_uids
        self._aggregate_by = aggregate_by
        self._segments = build_plot_segments(
            state.nodes,
            state.edges,
            total_score,
            max_depth=plot_depth,
            root_uid=state._root_node.unique_id,
            metadata_lookup=metadata_lookup,
            included_uids=included_uids,
            aggregate_by=aggregate_by,
        )
        if self._segments:
            self._max_direct_pct = max(
                abs(s["direct_pct"]) for s in self._segments
            ) or 100.0
        else:
            self._max_direct_pct = 100.0
        self.plot()

    @staticmethod
    def _segment_label(seg: dict) -> str:
        """Product or aggregate key — on-plot labels only."""
        if seg.get("is_aggregate") and seg.get("aggregate_key"):
            return str(seg["aggregate_key"])
        return str(seg.get("product") or "").strip()

    def _label_scale(self) -> float:
        """Figure-width factor for label visibility and char budget."""
        if not self._canvas_has_size():
            return 1.0
        fig_w, _ = self.get_canvas_size_in_inches()
        return max(0.7, min(1.6, fig_w / 6.0))

    def _chars_for_fraction(self, frac: float, fontsize: float = 6.0) -> int:
        """Rough char count for a label spanning ``frac`` of the figure width."""
        if frac <= 0:
            return 0
        scale = self._label_scale()
        if not self._canvas_has_size():
            return max(6, int(frac * 50 * scale))
        fig_w, _ = self.get_canvas_size_in_inches()
        return max(6, int(fig_w * frac * 72 / (fontsize * 0.52) * scale))

    @staticmethod
    def _lines_for_row_height(row_h_in: float, fontsize: float) -> int:
        """Wrap line count that fits in a tier-bar row height."""
        if row_h_in <= 0:
            return 1
        line_h_in = (fontsize / 72.0) * 1.08
        return max(1, min(6, int(row_h_in / line_h_in)))

    def _tier_bar_text_layout(
        self,
        max_depth: int,
        *,
        row_height_frac: float = 0.85,
        fontsize: float = 6.0,
    ) -> tuple[int, float]:
        """Shared wrap lines + font size from tier row height (width varies per bar)."""
        if max_depth <= 0:
            return 1, fontsize
        if not self._canvas_has_size():
            return 3, fontsize
        _, fig_h = self.get_canvas_size_in_inches()
        row_h_in = (fig_h / max_depth) * row_height_frac
        # Estimate line capacity at the smallest tier-bar font we use.
        max_lines = self._lines_for_row_height(row_h_in, 4.5)
        return max_lines, fontsize

    @staticmethod
    def _tier_bar_fontsize(width: float, base: float) -> float:
        """Smaller font in narrow bars so wrapped text stays inside horizontally."""
        if width < 0.04:
            return min(base, 4.5)
        if width < 0.08:
            return min(base, 5.0)
        if width < 0.12:
            return min(base, 5.5)
        return base

    def _tier_bar_chars_per_line(self, width: float, fontsize: float) -> int:
        """Conservative chars per line for a bar's horizontal span."""
        usable = max(width * 0.92, 0.001)
        chars = self._chars_for_fraction(usable, fontsize)
        return max(3, int(chars * 0.55))

    @staticmethod
    def _icicle_column_fontsize(col_w: float, base: float) -> float:
        """Smaller font in narrow tier columns."""
        if col_w < 0.08:
            return min(base, 4.5)
        if col_w < 0.15:
            return min(base, 5.0)
        if col_w < 0.22:
            return min(base, 5.5)
        return base

    def _icicle_chars_per_line(self, col_width_frac: float, fontsize: float) -> int:
        """Chars per line from shared column width (same for every icicle cell)."""
        usable = max(col_width_frac * 0.88, 0.001)
        chars = self._chars_for_fraction(usable, fontsize)
        return max(3, int(chars * 0.55))

    def _icicle_max_lines(self, height_frac: float, fontsize: float) -> int:
        """Wrap lines allowed by a cell's vertical span."""
        if height_frac <= 0:
            return 1
        if not self._canvas_has_size():
            return max(2, min(6, int(height_frac * 50)))
        _, fig_h = self.get_canvas_size_in_inches()
        lines = self._lines_for_row_height(height_frac * fig_h, fontsize)
        if height_frac >= 0.06:
            lines = max(2, lines)
        return lines

    @staticmethod
    def _label_worth_showing(display: str) -> bool:
        stripped = display.strip()
        return bool(stripped) and stripped not in ("…", "...")

    @staticmethod
    def _sunburst_tangent_rotation(mid_rad: float) -> float:
        """Rotation (deg) for text aligned tangentially within a polar wedge."""
        deg = (np.degrees(mid_rad) + 360) % 360
        rotation = deg
        if 90 < deg <= 270:
            rotation += 180
        return rotation % 360

    @staticmethod
    def _sunburst_radial_rotation(mid_rad: float) -> float:
        """Rotation (deg) for text aligned radially (outward from centre)."""
        deg = (np.degrees(mid_rad) + 360) % 360
        rotation = deg - 90
        if 90 < deg <= 270:
            rotation += 180
        return rotation % 360

    def _chars_for_radial_span(self, r_span_frac: float, fontsize: float = 6.0) -> int:
        """Char count for text running outward along a ring's radial thickness."""
        if r_span_frac <= 0:
            return 0
        scale = self._label_scale()
        if not self._canvas_has_size():
            return max(4, int(r_span_frac * 40 * scale))
        fig_w, fig_h = self.get_canvas_size_in_inches()
        span_in = min(fig_w, fig_h) * 0.5 * r_span_frac
        return max(4, int(span_in * 72 / (fontsize * 0.52) * scale))

    def _chars_for_arc(
        self,
        radius_frac: float,
        width_rad: float,
        fontsize: float,
    ) -> int:
        """Char count for text running tangentially along a wedge arc."""
        if radius_frac <= 0 or width_rad <= 0:
            return 0
        scale = self._label_scale()
        if not self._canvas_has_size():
            return max(4, int(width_rad * radius_frac * 80 * scale))
        fig_w, fig_h = self.get_canvas_size_in_inches()
        r_in = min(fig_w, fig_h) * 0.5 * radius_frac
        arc_in = r_in * width_rad
        return max(4, int(arc_in * 72 / (fontsize * 0.55) * scale * 0.88))

    def _sunburst_ring_lines(self, ring_span: float, fontsize: float) -> int:
        if not self._canvas_has_size():
            return 2
        fig_w, fig_h = self.get_canvas_size_in_inches()
        ring_span_in = min(fig_w, fig_h) * 0.5 * ring_span
        return min(3, max(1, self._lines_for_row_height(ring_span_in, fontsize)))

    def _sunburst_fontsize(self, frac: float) -> float:
        if frac < 0.035:
            return 4.0
        if frac < 0.06:
            return 4.5
        if frac < 0.11:
            return 5.0
        return 5.5

    def _sunburst_label_layout(
        self,
        label: str,
        *,
        frac: float,
        width_rad: float,
        r0: float,
        r1: float,
        mid: float,
        tier: int,
        ring_w: float,
        min_frac: float,
    ) -> dict | None:
        """Label geometry for one sunburst wedge, or None if too cramped."""
        if not label or frac <= min_frac:
            return None
        if tier == 0 and frac > 0.35:
            return None

        ring_span = r1 - r0
        r_mid = (r0 + r1) * 0.5
        if frac < 0.018:
            return None

        fontsize = self._sunburst_fontsize(frac)
        ring_lines = self._sunburst_ring_lines(ring_span, fontsize)
        arc_chars = self._chars_for_arc(r_mid, width_rad, fontsize)

        # Wide wedges: tangential text along the arc (more readable, uses angular width).
        if frac >= 0.02 and arc_chars >= 5:
            max_lines = 1
            if frac >= 0.045 and ring_lines >= 2:
                max_lines = 2
            if frac >= 0.09 and ring_lines >= 3:
                max_lines = 3
            chars_per_line = max(
                4,
                int(arc_chars * (0.92 if max_lines == 1 else 0.82)),
            )
            display = self._fit_label(label, chars_per_line, max_lines=max_lines)
            if not self._label_worth_showing(display):
                return None
            return {
                "x": mid,
                "y": r_mid,
                "s": display,
                "ha": "center",
                "va": "center",
                "fontsize": fontsize,
                "rotation": self._sunburst_tangent_rotation(mid),
                "rotation_mode": "anchor",
            }

        radial_chars = self._chars_for_radial_span(ring_span * 0.88, fontsize)
        if radial_chars < 3:
            return None
        max_lines = 2 if ring_lines >= 2 and ring_span > ring_w * 0.3 else 1
        display = self._fit_label_chars(
            label,
            max(3, radial_chars),
            max_lines=max_lines,
        )
        if not self._label_worth_showing(display):
            return None
        return {
            "x": mid,
            "y": r0 + ring_span * 0.14,
            "s": display,
            "ha": "left",
            "va": "center",
            "fontsize": fontsize,
            "rotation": self._sunburst_radial_rotation(mid),
            "rotation_mode": "anchor",
        }

    @staticmethod
    def _wrap_label_words(text: str, width: int) -> str:
        return textwrap.fill(
            text,
            width=max(4, width),
            break_long_words=False,
            replace_whitespace=False,
        )

    @staticmethod
    def _clip_text_to_patch(txt, patch) -> None:
        try:
            txt.set_clip_path(patch.get_path(), patch.get_transform())
        except (TypeError, AttributeError):
            txt.set_clip_path(patch)

    @staticmethod
    def _fit_label_chars(text: str, max_chars: int, max_lines: int = 1) -> str:
        """Fixed-width character breaks (may split mid-word)."""
        if not text:
            return ""
        w = max(1, max_chars)
        if max_lines <= 1:
            return text if len(text) <= w else text[: w - 1] + "…"
        lines: list[str] = []
        pos = 0
        for line_no in range(max_lines):
            if pos >= len(text):
                break
            if line_no == max_lines - 1:
                tail = text[pos:]
                lines.append(tail if len(tail) <= w else tail[: w - 1] + "…")
                break
            lines.append(text[pos : pos + w])
            pos += w
        return "\n".join(lines)

    @staticmethod
    def _fit_label(text: str, max_chars: int, max_lines: int = 1) -> str:
        """Word-aware truncate or wrap for on-plot segment labels."""
        if not text:
            return ""
        width = max(4, max_chars)
        if max_lines <= 1:
            return textwrap.shorten(text, width=width, placeholder="…")
        wrapped = ContributionTreePlot._wrap_label_words(text, width)
        lines = wrapped.splitlines()
        if len(lines) <= max_lines:
            return wrapped
        kept = lines[: max_lines - 1]
        remainder = " ".join(lines[max_lines - 1 :])
        kept.append(textwrap.shorten(remainder, width=width, placeholder="…"))
        return "\n".join(kept)

    def plot(self) -> None:
        self._hover_targets = []
        if self._state is None or self._total_score == 0.0:
            self.show_empty()
            return
        if not self._segments:
            self.show_empty("Use Adjust to explore the supply chain.")
            return

        dispatch = {
            PLOT_SUNBURST: self._plot_sunburst,
            PLOT_TIER_BARS: self._plot_tier_bars,
            PLOT_ICICLE: self._plot_icicle,
        }
        dispatch.get(self._mode, self._plot_icicle)()
        self.finish_plot(on_hover=self._hover_callback, on_click=self._click_callback)


    def _segment_at(self, event) -> dict | None:
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return None
        if self._mode == PLOT_SUNBURST:
            return self._sunburst_segment_at(event)
        x, y = float(event.xdata), float(event.ydata)
        depth = max(1, self._plot_depth)
        for seg in reversed(self._segments):
            lo, hi = seg["x0"], seg["x1"]
            if lo > hi:
                lo, hi = hi, lo
            if self._mode == PLOT_TIER_BARS:
                if abs(y - seg["tier"]) <= 0.45 and lo <= x <= max(hi, lo + 0.003):
                    return seg
            elif 0 <= x <= 1 and 0 <= y <= 1:
                if seg["tier"] == min(int(x / (1.0 / depth)), depth - 1) and lo <= y <= hi:
                    return seg
        return None

    def _click_callback(self, event) -> None:
        if self._on_segment_clicked is None:
            return
        seg = self._segment_at(event)
        if seg is not None:
            self._on_segment_clicked(seg)

    def _hover_callback(self, event):
        if event.inaxes is None:
            return None
        seg = self._segment_at(event)
        if seg is not None:
            return self._format_segment_tooltip(seg)
        return None

    def _sunburst_segment_at(self, event):
        """Polar hit-test — inner-ring (tier 0) wedges miss ``contains()`` on bar patches."""
        if event.xdata is None or event.ydata is None:
            return None
        max_depth = self._plot_depth
        ring_w = 1.0 / (max_depth + 1)
        r = event.ydata
        tier = None
        for t in range(max_depth):
            r0 = ring_w * (t + 0.05)
            r1 = ring_w * (t + 0.95)
            if r0 <= r <= r1:
                tier = t
                break
        if tier is None:
            return None
        theta = float(event.xdata) % (2 * np.pi)
        for seg in self._segments:
            if seg["tier"] != tier:
                continue
            t0 = seg["x0"] * 2 * np.pi
            t1 = seg["x1"] * 2 * np.pi
            if t0 <= theta <= t1:
                return seg
        return None

    @staticmethod
    def _format_abs(value: float) -> str:
        a = abs(value)
        if a >= 100:
            return f"{value:.2f}"
        if a >= 1:
            return f"{value:.3f}"
        if a >= 0.01:
            return f"{value:.4f}"
        return f"{value:.2e}"

    def _format_segment_tooltip(self, seg: dict) -> str:
        unit = self._unit or seg.get("unit") or ""
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
            f"({self._format_abs(seg['cumulative_score'])} {unit})".rstrip()
        )
        lines.append(
            f"Direct impact: {seg['direct_pct']:.2f}% "
            f"({self._format_abs(seg['direct_emissions_score'])} {unit})".rstrip()
        )
        return "\n".join(lines)


    def _register_hover(self, artist, seg: dict) -> None:
        self._hover_targets.append((artist, seg))

    def _plot_sunburst(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111, polar=True)
        self.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_axis_off()

        max_depth = self._plot_depth
        ring_w = 1.0 / (max_depth + 1)
        scale = self._label_scale()
        min_frac = 0.028 / scale

        for seg in self._segments:
            tier = seg["tier"]
            r0 = ring_w * (tier + 0.05)
            r1 = ring_w * (tier + 0.95)
            theta = seg["x0"] * 2 * np.pi
            width = (seg["x1"] - seg["x0"]) * 2 * np.pi
            colour = self._segment_color(seg["direct_pct"])
            bar = ax.bar(
                x=theta,
                width=width,
                bottom=r0,
                height=ring_w * 0.9,
                color=colour,
                edgecolor=SEGMENT_EDGE_COLOR,
                linewidth=SEGMENT_EDGE_WIDTH,
                align="edge",
            )
            patch = bar.patches[0]
            self._register_hover(patch, seg)

            label = self._segment_label(seg)
            frac = width / (2 * np.pi)
            layout = self._sunburst_label_layout(
                label,
                frac=frac,
                width_rad=width,
                r0=r0,
                r1=r1,
                mid=theta + width / 2,
                tier=tier,
                ring_w=ring_w,
                min_frac=min_frac,
            )
            if layout is None:
                continue
            txt = ax.text(
                layout["x"],
                layout["y"],
                layout["s"],
                ha=layout["ha"],
                va=layout["va"],
                fontsize=layout["fontsize"],
                color=self._theme_text_color(),
                rotation=layout["rotation"],
                rotation_mode=layout["rotation_mode"],
                clip_on=True,
            )
            self._clip_text_to_patch(txt, patch)

        ax.text(
            0,
            0,
            "RF",
            ha="center",
            va="center",
            fontsize=8,
            color=self._theme_text_color(),
        )

    def _plot_tier_bars(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.12, right=0.99, top=0.98, bottom=0.04)
        row_h = 1.0
        bar_height_frac = 0.85
        bar_h = row_h * bar_height_frac
        max_depth = self._plot_depth
        scale = self._label_scale()
        min_frac = 0.025 / scale
        max_lines, base_fontsize = self._tier_bar_text_layout(
            max_depth, row_height_frac=bar_height_frac, fontsize=6.0
        )

        for tier in range(max_depth):
            ax.text(
                -0.02,
                tier,
                f"Tier {tier}",
                ha="right",
                va="center",
                fontsize=8,
                color=self._theme_text_color(),
            )

        rects: list[Rectangle] = []
        for seg in self._segments:
            tier = seg["tier"]
            x0, x1 = seg["x0"], seg["x1"]
            width = max(x1 - x0, 0.003)
            if x1 - x0 < 0.003:
                x0 = (seg["x0"] + seg["x1"]) / 2 - width / 2
            colour = self._segment_color(seg["direct_pct"])
            rect = Rectangle(
                (x0, tier - bar_h / 2),
                width,
                bar_h,
                facecolor=colour,
                edgecolor=SEGMENT_EDGE_COLOR,
                linewidth=SEGMENT_EDGE_WIDTH,
            )
            rects.append(rect)
            label = self._segment_label(seg)
            if not label or width <= min_frac:
                continue
            fontsize = self._tier_bar_fontsize(width, base_fontsize)
            chars_per_line = self._tier_bar_chars_per_line(width, fontsize)
            if chars_per_line < 3:
                continue
            display = self._fit_label_chars(label, chars_per_line, max_lines=max_lines)
            if not self._label_worth_showing(display):
                continue
            ax.text(
                x0 + width / 2,
                tier,
                display,
                ha="center",
                va="center",
                fontsize=fontsize,
                color=self._theme_text_color(),
                clip_on=True,
            )

        if rects:
            ax.add_collection(PatchCollection(rects, match_original=True))
        ax.set_xlim(0, 1)
        ax.set_ylim(max_depth - 0.5, -0.5)
        ax.set_yticks([])
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    def _plot_icicle(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.figure.subplots_adjust(left=0.02, right=0.99, top=0.90, bottom=0.04)
        max_depth = max(1, self._plot_depth)
        col_w = 1.0 / max_depth
        scale = self._label_scale()
        min_height = 0.02 / scale
        col_width_frac = col_w * 0.97
        base_fontsize = 6.0
        col_fontsize = self._icicle_column_fontsize(col_w, base_fontsize)
        chars_per_line = self._icicle_chars_per_line(col_width_frac, col_fontsize)
        cell_w = col_w * 0.97

        for tier in range(max_depth):
            ax.text(
                (tier + 0.5) * col_w,
                1.02,
                f"Tier {tier}",
                ha="center",
                va="bottom",
                fontsize=8,
                color=self._theme_text_color(),
                transform=ax.get_xaxis_transform(),
            )

        rects: list[Rectangle] = []
        for seg in self._segments:
            tier = seg["tier"]
            x0 = tier * col_w
            y0 = seg["x0"]
            height = seg["x1"] - seg["x0"]
            colour = self._segment_color(seg["direct_pct"])
            rects.append(
                Rectangle(
                    (x0, y0),
                    cell_w,
                    height,
                    facecolor=colour,
                    edgecolor=SEGMENT_EDGE_COLOR,
                    linewidth=SEGMENT_EDGE_WIDTH,
                )
            )
            label = self._segment_label(seg)
            if not label or abs(height) <= min_height:
                continue
            fontsize = col_fontsize
            if abs(height) < 0.04:
                fontsize = min(fontsize, 4.5)
            elif abs(height) < 0.07:
                fontsize = min(fontsize, 5.0)
            max_lines = self._icicle_max_lines(abs(height) * 0.95, fontsize)
            if len(label) > chars_per_line and max_lines < 2:
                max_lines = 2
            display = self._fit_label_chars(label, chars_per_line, max_lines=max_lines)
            if not self._label_worth_showing(display):
                continue
            ax.text(
                x0 + cell_w / 2,
                y0 + height / 2,
                display,
                va="center",
                ha="center",
                fontsize=fontsize,
                color=self._theme_text_color(),
                clip_on=True,
            )

        if rects:
            ax.add_collection(PatchCollection(rects, match_original=True))
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    def export_figure(self, path: str, selected_filter: str = "") -> None:
        """Save the current matplotlib plot to disk."""
        lower = path.lower()
        if not lower.endswith((".png", ".svg")):
            path += ".svg" if "SVG" in selected_filter else ".png"
        # Screen figures are often ~100 dpi; export PNG at print-quality dpi.
        kwargs = {"bbox_inches": "tight"}
        if path.lower().endswith(".png"):
            kwargs["dpi"] = 300
        self.figure.savefig(path, **kwargs)
