"""Matplotlib plot widget base for Activity Browser LCA results.

Subclasses in ``activity_browser.app.pages.lca_results.plots`` implement
:meth:`ABPlot.plot` and call :meth:`finish_plot` when drawing is done.

Shared concerns handled here:
  - Qt scroll-area sizing (zero width hint, figure sync on resize)
  - Label shortening / wrapping (driven by per-tab ``full_labels``)
  - Series color palette, bar styling, signed-value grids
  - Hover tooltips on truncated tick labels, bars, and legends
  - Multi-panel figures via :meth:`set_axis_contexts`
"""

from __future__ import annotations

import math

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
except ImportError:  # matplotlib < 3.5
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib import colors as mcolors
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from activity_browser.bwutils.commontasks import shorten_label, wrap_text
from activity_browser.bwutils.contribution_labels import is_rest_row
from activity_browser.ui.core.application import ABApplication

_GOLDEN_RATIO = 0.618033988749895
_BASE_SERIES_PALETTE: tuple[tuple[float, float, float, float], ...] = tuple(
    plt.get_cmap("tab10").colors
) + tuple(plt.get_cmap("tab20").colors)
_GSA_TYPE_ORDER = (
    "technosphere",
    "biosphere",
    "characterization factor",
    "parameter",
)


def lca_results_tab_from_widget(widget) -> object | None:
    """Walk parents to the LCA results sub-tab with display options."""
    node = widget
    while node is not None:
        if hasattr(node, "full_labels"):
            parent = getattr(node, "parent", None)
            parent = parent() if callable(parent) else parent
            if parent is not None and hasattr(parent, "mlca"):
                return node
        parent = getattr(node, "parent", None)
        node = parent() if callable(parent) else parent
    return None


class ABFigureCanvas(FigureCanvasQTAgg):
    """Canvas with zero width hint so scroll areas do not widen the main window."""

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(0, 0)

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        return self.sizeHint()


class ABPlot(QtWidgets.QWidget):
    """Matplotlib figure embedded in Qt; subclasses implement :meth:`plot`."""

    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    FONT_SIZE = 9
    LABEL_MAX_LENGTH = 40
    AXIS_LABEL_WRAP_LENGTH = 20
    CATEGORY_ROTATE_LABELS_ABOVE = 3
    HORIZONTAL_LABEL_WIDTH_FRACTION = 0.42
    HORIZONTAL_AXIS_LABEL_WRAP_LENGTH = 40

    REST_BAR_COLOR = (0.8, 0.8, 0.8, 1.0)
    BAR_EDGE_WIDTH = 0.3

    @classmethod
    def bar_edge_color(cls) -> str:
        """Bar outline color matching the active axes background."""
        return plt.rcParams["axes.facecolor"]

    @classmethod
    def zero_line_color(cls) -> str:
        """Zero baseline color matching the active matplotlib style."""
        return plt.rcParams["axes.edgecolor"]

    # --- series color palette -------------------------------------------------

    @classmethod
    def series_color(cls, index: int) -> tuple[float, float, float, float]:
        """RGBA for categorical series ``index`` (30 curated colors, then golden-ratio hues)."""
        if index < len(_BASE_SERIES_PALETTE):
            return _BASE_SERIES_PALETTE[index]
        hue = (index * _GOLDEN_RATIO) % 1.0
        rgb = mcolors.hsv_to_rgb((hue, 0.72, 0.88))
        return (float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)

    @classmethod
    def series_colors(cls, n: int) -> np.ndarray:
        if n <= 0:
            return np.empty((0, 4))
        return np.array([cls.series_color(i) for i in range(n)])

    @classmethod
    def gsa_type_color(cls, gsa_type: str) -> tuple[float, float, float, float]:
        key = str(gsa_type).strip().lower()
        if key in _GSA_TYPE_ORDER:
            return cls.series_color(_GSA_TYPE_ORDER.index(key))
        return (0.5, 0.5, 0.5, 1.0)

    @classmethod
    def stack_contributor_colors(
        cls, full_rows: list[str], display_rows: list[str]
    ) -> list:
        """One palette color per contributor; grey for Rest (+)/(−) rows."""
        n = sum(
            1
            for full, disp in zip(full_rows, display_rows)
            if not is_rest_row(full) and not is_rest_row(disp)
        )
        palette = cls.series_colors(n)
        colors: list = []
        pal_i = 0
        for full, disp in zip(full_rows, display_rows):
            if is_rest_row(full) or is_rest_row(disp):
                colors.append(cls.REST_BAR_COLOR)
            else:
                colors.append(palette[pal_i])
                pal_i += 1
        return colors

    @staticmethod
    def near_square_subplot_grid(n: int) -> tuple[int, int]:
        """``(nrows, ncols)`` for *n* panels, as square as practical."""
        if n <= 0:
            return 0, 0
        best: tuple[tuple[int, int, int], int, int] | None = None
        for ncols in range(1, n + 1):
            nrows = math.ceil(n / ncols)
            score = (abs(ncols - nrows), ncols * nrows - n, 0 if ncols >= nrows else 1)
            if best is None or score < best[0]:
                best = (score, nrows, ncols)
        assert best is not None
        return best[1], best[2]

    def legend_column_width_ratio(self) -> float:
        """GridSpec width fraction for a shared legend column."""
        return max(0.12, min(0.4, self.LABEL_MAX_LENGTH / 160.0))

    # --- bar / axis drawing helpers -------------------------------------------

    @staticmethod
    def set_signed_value_grid(ax, *, horizontal: bool) -> None:
        """Zero reference line and dashed grid on the value axis."""
        zero_color = ABPlot.zero_line_color()
        ax.set_axisbelow(True)
        if horizontal:
            ax.axvline(0, color=zero_color, linewidth=0.8, zorder=1)
            ax.grid(axis="x", linestyle="dashed", color="grey", alpha=0.7)
        else:
            ax.axhline(0, color=zero_color, linewidth=0.8, zorder=1)
            ax.grid(axis="y", linestyle="dashed", color="grey", alpha=0.7)

    def plot_bar_strip(
        self,
        ax,
        positions,
        heights,
        thickness: float,
        color,
        label: str,
        *,
        horizontal: bool,
    ) -> None:
        kw = dict(
            label=label,
            color=[color] * len(heights),
            edgecolor=self.bar_edge_color(),
            linewidth=self.BAR_EDGE_WIDTH,
        )
        size = thickness * 0.92
        if horizontal:
            ax.barh(positions, heights, height=size, **kw)
        else:
            ax.bar(positions, heights, width=size, **kw)

    def set_category_positions(self, ax, n_categories: int, *, horizontal: bool) -> np.ndarray:
        """Place category tick positions; invert y for horizontal bars."""
        positions = np.arange(n_categories)
        if horizontal:
            ax.set_yticks(positions)
            ax.invert_yaxis()
        else:
            ax.set_xticks(positions)
        return positions

    @staticmethod
    def category_axis_tooltips(
        labels: list[str], *, horizontal: bool
    ) -> tuple[list[str] | None, list[str] | None]:
        """``(tooltip_x, tooltip_y)`` for :meth:`finish_plot` from category labels."""
        if horizontal:
            return None, labels
        return labels, None

    # --- construction / Qt sizing -----------------------------------------------

    def __init__(self, parent=None):
        super().__init__(parent)

        self.figure = Figure(constrained_layout=True)
        self.canvas = ABFigureCanvas(self.figure)
        self.canvas.setMinimumHeight(0)
        self.canvas.setMinimumWidth(0)
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setMinimumWidth(0)

        self.ax = self.figure.add_subplot(111)
        self.plot_name = "Figure"
        self._hover_cid = None
        self._tooltip_y: list[str] = []
        self._tooltip_x: list[str] = []
        self._tooltip_legend: list[str] = []

        self.full_row_labels: list[str] = []
        self.full_col_labels: list[str] = []
        self.plot_unit: str | None = None
        self.plot_relative: bool = False
        self.col_scores: dict[str, float] = {}
        self.col_units: dict[str, str] = {}
        self._bar_values: np.ndarray | None = None
        self._bar_errors: np.ndarray | None = None
        self._hist_series: list[np.ndarray] = []
        self._axis_contexts: list[dict] = []
        self._current_bar_ctx: dict | None = None

        self._sync_plot_to_theme()
        ab_app = QtWidgets.QApplication.instance()
        if isinstance(ab_app, ABApplication):
            ab_app.theme_changed.connect(self._on_theme_changed)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas, 1)
        self.setLayout(layout)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.updateGeometry()

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(0, 0)

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(0, 0)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_figure_sync()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._schedule_figure_sync()

    def _device_pixel_ratio(self) -> float:
        if hasattr(self.canvas, "devicePixelRatioF"):
            return float(self.canvas.devicePixelRatioF())
        return float(self.canvas.devicePixelRatio())

    def _canvas_has_size(self) -> bool:
        return max(self.canvas.width(), self.width()) > 0 and max(
            self.canvas.height(), self.height()
        ) > 0

    def _qt_physical_pixel_size(self) -> tuple[float, float]:
        dpr = self._device_pixel_ratio()
        cw = max(self.canvas.width(), self.width(), 1)
        ch = max(self.canvas.height(), self.height(), 1)
        return cw * dpr, ch * dpr

    def get_canvas_size_in_inches(self) -> tuple[float, float]:
        w_px, h_px = self._qt_physical_pixel_size()
        return w_px / self.figure.dpi, h_px / self.figure.dpi

    def sync_figure_to_widget(self) -> None:
        if not self._canvas_has_size():
            return
        w_px, h_px = self._qt_physical_pixel_size()
        dpi = self.figure.dpi
        self.figure.set_size_inches(w_px / dpi, h_px / dpi, forward=False)
        self.canvas.draw_idle()

    def _schedule_figure_sync(self) -> None:
        QtCore.QTimer.singleShot(0, self.sync_figure_to_widget)

    def set_minimum_height_for_figure_inches(self, height_inches: float) -> None:
        phy_px = height_inches * self.figure.dpi
        logical = max(int(math.ceil(phy_px / self._device_pixel_ratio())), 1)
        self.setMinimumHeight(logical)

    def reset_minimum_figure_height(self) -> None:
        self.setMinimumHeight(0)

    # --- LCA results tab display options ----------------------------------------

    def _lca_results_tab(self):
        return lca_results_tab_from_widget(self)

    def use_full_labels(self) -> bool:
        tab = self._lca_results_tab()
        return bool(getattr(tab, "full_labels", False))

    def use_horizontal_bars(self) -> bool:
        tab = self._lca_results_tab()
        return bool(getattr(tab, "horizontal_bars", False))

    # --- label formatting -------------------------------------------------------

    def shorten_labels(self, labels: list[str], max_length: int | None = None) -> list[str]:
        if isinstance(labels, str):
            labels = [labels]
        if self.use_full_labels():
            return [str(label) for label in labels]
        ml = max_length or self.LABEL_MAX_LENGTH
        return [shorten_label(str(label), ml) for label in labels]

    def format_title(self, title: str, max_length: int | None = None) -> str:
        ml = max_length or self.LABEL_MAX_LENGTH
        if self.use_full_labels():
            return self.wrap_labels_to_lines([str(title)], chars_per_line=ml, max_lines=3)[0]
        return shorten_label(str(title), ml)

    def legend_labels(self, labels: list[str], max_length: int | None = None) -> list[str]:
        if isinstance(labels, str):
            labels = [labels]
        ml = max_length or self.LABEL_MAX_LENGTH
        if self.use_full_labels():
            return [wrap_text(str(label), max_length=ml) for label in labels]
        return [shorten_label(str(label), ml) for label in labels]

    @staticmethod
    def label_needs_tooltip(display: str, full: str) -> bool:
        display_n, full_n = str(display).strip(), str(full).strip()
        return bool(full_n) and display_n != full_n

    def wrap_labels_to_lines(
        self,
        labels: list[str],
        *,
        chars_per_line: int,
        max_lines: int = 3,
    ) -> list[str]:
        width = max(4, chars_per_line)
        out: list[str] = []
        for label in labels:
            wrapped = wrap_text(str(label), max_length=width)
            lines = wrapped.splitlines()
            if len(lines) <= max_lines:
                out.append(wrapped)
                continue
            kept = lines[: max_lines - 1]
            remainder = " ".join(lines[max_lines - 1 :])
            kept.append(shorten_label(remainder, width))
            out.append("\n".join(kept))
        return out

    def _tick_label_chars_per_line(
        self,
        n_ticks: int,
        *,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
        horizontal: bool = False,
    ) -> int:
        width_in, _ = self.get_canvas_size_in_inches()
        if width_in < 2:
            width_in = 6.0
        panel_width_in = width_in / (max(grid_ncols, 1) + max(legend_width_ratio, 0.0))
        if horizontal:
            chars = max(12, int(panel_width_in * self.HORIZONTAL_LABEL_WIDTH_FRACTION / 0.085))
            cap = self.HORIZONTAL_AXIS_LABEL_WRAP_LENGTH
        else:
            chars = max(5, int(panel_width_in / max(n_ticks, 1) / 0.085))
            cap = self.AXIS_LABEL_WRAP_LENGTH
        if self.use_full_labels():
            cap = max(cap, self.LABEL_MAX_LENGTH)
        return min(chars, cap)

    def _set_category_ticklabels(
        self,
        ax,
        group_labels: list[str],
        *,
        horizontal: bool,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
        rotate_above: int | None = None,
    ) -> None:
        if not group_labels:
            return

        n_groups = len(group_labels)
        threshold = rotate_above if rotate_above is not None else self.CATEGORY_ROTATE_LABELS_ABOVE
        use_rotation = not horizontal and n_groups > threshold
        chars = self._tick_label_chars_per_line(
            n_groups,
            grid_ncols=grid_ncols,
            legend_width_ratio=legend_width_ratio,
            horizontal=horizontal,
        )

        if use_rotation and self.use_full_labels():
            display = [
                wrap_text(" ".join(str(label).split()), max_length=self.LABEL_MAX_LENGTH)
                for label in group_labels
            ]
        else:
            wrap_width = max(chars, 18) if use_rotation else chars
            display = self.wrap_labels_to_lines(
                group_labels,
                chars_per_line=wrap_width,
                max_lines=4 if horizontal else 3,
            )

        axis = "y" if horizontal else "x"
        if use_rotation:
            ha, rotation, rotation_mode = "right", 45, "anchor"
        elif axis == "x":
            ha, rotation, rotation_mode = "center", 0, "default"
        else:
            ha, rotation, rotation_mode = "right", 0, "default"

        tick_kw = dict(
            ha=ha, rotation=rotation, rotation_mode=rotation_mode, fontsize=self.FONT_SIZE
        )
        setter = ax.set_yticklabels if horizontal else ax.set_xticklabels
        setter(display, **tick_kw)
        ax.tick_params(axis=axis, pad=2)

    def apply_axis_fonts(self, ax) -> None:
        size = self.FONT_SIZE
        for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
            label.set_fontsize(size)
        for text in (ax.xaxis.label, ax.yaxis.label, ax.title):
            if text:
                text.set_fontsize(size)

    def apply_standard_fonts(self) -> None:
        axes = [ctx["ax"] for ctx in self._axis_contexts] if self._axis_contexts else []
        if not axes and self.ax is not None:
            axes = [self.ax]
        for ax in axes:
            self.apply_axis_fonts(ax)
        for legend in self.figure.legends:
            for text in legend.get_texts():
                text.set_fontsize(self.FONT_SIZE)

    # --- plot data context (tooltips) -------------------------------------------

    def set_axis_contexts(self, contexts: list[dict]) -> None:
        """Register per-axes tooltip data for multi-panel figures.

        Each dict: ``ax``, ``bar_values``, optional ``tooltip_x`` / ``tooltip_y``,
        ``full_title``, and subclass-specific keys (e.g. ``panel``).
        """
        self._axis_contexts = list(contexts)

    def _tooltip_axis_contexts(self) -> list[dict]:
        if self._axis_contexts:
            return self._axis_contexts
        if self.ax is None:
            return []
        return [
            {
                "ax": self.ax,
                "tooltip_x": self._tooltip_x,
                "tooltip_y": self._tooltip_y,
                "bar_values": self._bar_values,
                "full_title": None,
            }
        ]

    def set_plot_context(
        self,
        *,
        unit: str | None = None,
        relative: bool = False,
        row_labels: list[str] | None = None,
        col_labels: list[str] | None = None,
        bar_values: np.ndarray | None = None,
        bar_errors: np.ndarray | None = None,
        col_scores: dict[str, float] | None = None,
        col_units: dict[str, str] | None = None,
        hist_series: list[np.ndarray] | None = None,
    ) -> None:
        """Store labels and values used by default bar/histogram tooltips."""
        self.plot_unit = unit
        self.plot_relative = relative
        self.full_row_labels = list(row_labels) if row_labels else []
        self.full_col_labels = list(col_labels) if col_labels else []
        self._bar_values = bar_values
        self._bar_errors = bar_errors
        self.col_scores = dict(col_scores) if col_scores else {}
        self.col_units = dict(col_units) if col_units else {}
        self._hist_series = list(hist_series) if hist_series else []

    @staticmethod
    def compose_bar_tooltip(header_lines: list[str], value_lines: list[str]) -> str:
        return "\n".join([*header_lines, *value_lines])

    @staticmethod
    def tooltip_value_lines(
        value: float,
        *,
        relative: bool,
        unit: str | None = None,
        absolute_value: float | None = None,
        relative_share_percent: float | None = None,
        relative_already_percent: bool = False,
    ) -> list[str]:
        if relative:
            pct = f"{value:.1f}%" if relative_already_percent else f"{100.0 * value:.1f}%"
            lines = [pct]
            if absolute_value is not None:
                abs_line = f"{absolute_value:,.4g}"
                if unit:
                    abs_line += f" {unit}"
                lines.append(abs_line)
            return lines
        primary = f"{value:,.4g}"
        if unit:
            primary += f" {unit}"
        lines = [primary]
        if relative_share_percent is not None:
            lines.append(f"{relative_share_percent:.1f}%")
        return lines

    def format_bar_tooltip(self, series_idx: int, bar_idx: int, value: float) -> str:
        """Default grouped/stacked bar tooltip; override in subclasses."""
        bar = self.full_row_labels[bar_idx] if bar_idx < len(self.full_row_labels) else ""
        series = self.full_col_labels[series_idx] if series_idx < len(self.full_col_labels) else ""
        unit = self.col_units.get(bar) if self.col_units else self.plot_unit
        share_pct = None
        if not self.plot_relative and (score := self.col_scores.get(bar)):
            share_pct = 100.0 * value / score
        value_lines = self.tooltip_value_lines(
            value,
            relative=self.plot_relative,
            unit=unit,
            relative_share_percent=share_pct,
        )
        header = [series, bar] if len(self.full_col_labels) > 1 and series else [bar]
        return self.compose_bar_tooltip(header, value_lines)

    # --- hover tooltips ---------------------------------------------------------

    def bar_patch_tooltip(self, event) -> str | None:
        if event.inaxes is None:
            return None
        for ctx in self._tooltip_axis_contexts():
            if event.inaxes is not ctx["ax"]:
                continue
            bar_values = ctx.get("bar_values")
            if bar_values is None:
                continue
            ax = ctx["ax"]
            self._current_bar_ctx = ctx
            try:
                # Skip non-bar containers (e.g. ErrorbarContainer from bar ``yerr``).
                bar_containers = [
                    c for c in ax.containers if getattr(c, "patches", None)
                ]
                for series_idx, container in enumerate(bar_containers):
                    for bar_idx, patch in enumerate(container.patches):
                        inside, _ = patch.contains(event)
                        if not inside:
                            continue
                        if (
                            series_idx >= bar_values.shape[0]
                            or bar_idx >= bar_values.shape[1]
                        ):
                            continue
                        value = float(bar_values[series_idx, bar_idx])
                        if np.isnan(value):
                            return None
                        return self.format_bar_tooltip(series_idx, bar_idx, value)
            finally:
                self._current_bar_ctx = None
        return None

    def histogram_x_tooltip(self, event) -> str | None:
        if event.inaxes is not self.ax or event.xdata is None or not self._hist_series:
            return None
        x = float(event.xdata)
        for i, vals in enumerate(self._hist_series):
            if vals.size == 0:
                continue
            if float(np.min(vals)) <= x <= float(np.max(vals)):
                name = self.full_col_labels[i] if i < len(self.full_col_labels) else ""
                line = f"{x:,.4g}"
                if self.plot_unit:
                    line += f" {self.plot_unit}"
                return f"{name}\n{line}" if name else line
        return None

    def _legend_tooltip(self, event) -> str | None:
        if not self._tooltip_legend or event.x is None or event.y is None:
            return None
        renderer = self.figure.canvas.get_renderer()
        legends = [
            leg
            for leg in (
                *(ax.get_legend() for ax in self.figure.axes),
                *self.figure.legends,
            )
            if leg is not None
        ]
        for legend in legends:
            _, info = legend.contains(event)
            ind = info.get("ind") if info else None
            if ind is not None:
                try:
                    return str(self._tooltip_legend[int(ind[0])]).strip()
                except (IndexError, TypeError, ValueError):
                    pass
            for idx, handle in enumerate(legend.legend_handles):
                if handle.get_window_extent(renderer).contains(event.x, event.y):
                    try:
                        return str(self._tooltip_legend[idx]).strip()
                    except IndexError:
                        return None
            for idx, text in enumerate(legend.get_texts()):
                try:
                    full = str(self._tooltip_legend[idx]).strip()
                except IndexError:
                    continue
                if self.label_needs_tooltip(
                    text.get_text(), full
                ) and text.get_window_extent(renderer).contains(event.x, event.y):
                    return full
        return None

    def _truncated_label_tooltip(self, event) -> str | None:
        if event.x is None or event.y is None:
            return None
        tip = self._legend_tooltip(event)
        if tip is not None:
            return tip
        renderer = self.figure.canvas.get_renderer()
        for ctx in self._tooltip_axis_contexts():
            ax = ctx["ax"]
            for ticks, full_labels in (
                (ax.get_yticklabels(), ctx.get("tooltip_y") or []),
                (ax.get_xticklabels(), ctx.get("tooltip_x") or []),
            ):
                if not full_labels:
                    continue
                for tick, full in zip(ticks, full_labels):
                    if self.label_needs_tooltip(
                        tick.get_text(), full
                    ) and tick.get_window_extent(renderer).contains(event.x, event.y):
                        return full
            full_title = ctx.get("full_title") or ""
            if full_title and self.label_needs_tooltip(
                ax.title.get_text(), full_title
            ) and ax.title.get_window_extent(renderer).contains(event.x, event.y):
                return full_title
        return None

    def set_motion_tooltip(
        self,
        on_hover=None,
        *,
        y: list[str] | None = None,
        x: list[str] | None = None,
        legend: list[str] | None = None,
        offset: tuple[int, int] = (12, 12),
    ) -> None:
        self._tooltip_y = list(y) if y else []
        self._tooltip_x = list(x) if x else []
        self._tooltip_legend = list(legend) if legend else []
        self.clear_hover_tooltip()
        self.canvas.setMouseTracking(True)
        dx, dy = offset

        def on_motion(event):
            tip = self._truncated_label_tooltip(event)
            if tip is None:
                tip = self.bar_patch_tooltip(event)
            if tip is None:
                tip = self.histogram_x_tooltip(event)
            if tip is None and on_hover is not None:
                tip = on_hover(event)
            if tip:
                QtWidgets.QToolTip.showText(
                    QtGui.QCursor.pos() + QtCore.QPoint(dx, dy), tip, self.canvas
                )
            else:
                QtWidgets.QToolTip.hideText()

        self._hover_cid = self.canvas.mpl_connect("motion_notify_event", on_motion)

    def clear_hover_tooltip(self) -> None:
        if self._hover_cid is not None:
            self.canvas.mpl_disconnect(self._hover_cid)
            self._hover_cid = None
        QtWidgets.QToolTip.hideText()

    # --- plot lifecycle ---------------------------------------------------------

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def _sync_plot_to_theme(self) -> None:
        fig_color = plt.rcParams["figure.facecolor"]
        ax_color = plt.rcParams["axes.facecolor"]
        self.figure.patch.set_facecolor(fig_color)
        for ax in self.figure.axes:
            ax.set_facecolor(ax_color)
        if self.ax is not None and self.ax not in self.figure.axes:
            self.ax.set_facecolor(ax_color)
        qapp = QtWidgets.QApplication.instance()
        if qapp is not None:
            qcolor = qapp.palette().color(QtGui.QPalette.ColorRole.Window)
            bg = f"background-color: {qcolor.name()};"
            self.canvas.setStyleSheet(bg)
            self.setStyleSheet(bg)

    def _sync_plot_chrome_to_theme(self) -> None:
        self._sync_plot_to_theme()

    def _on_theme_changed(self) -> None:
        self._sync_plot_to_theme()
        if self.figure.axes:
            self.canvas.draw_idle()

    def reset_plot(self) -> None:
        self.clear_hover_tooltip()
        self._axis_contexts = []
        self._current_bar_ctx = None
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self._sync_plot_to_theme()

    def add_legend(self, *args, ax=None, **kwargs):
        kwargs.setdefault("ncol", 1)
        kwargs.setdefault("frameon", False)
        kwargs.setdefault("fontsize", self.FONT_SIZE)
        target = ax if ax is not None else self.ax
        legend = target.legend(*args, **kwargs)
        if legend is not None:
            for text in legend.get_texts():
                text.set_fontsize(self.FONT_SIZE)
        return legend

    def finish_plot(
        self,
        *,
        on_hover=None,
        tooltip_y: list[str] | None = None,
        tooltip_x: list[str] | None = None,
        tooltip_legend: list[str] | None = None,
    ) -> None:
        """Apply fonts, draw, and wire hover tooltips. Call once per :meth:`plot`."""
        self.apply_standard_fonts()
        self._sync_plot_to_theme()
        self.sync_figure_to_widget()
        if self._canvas_has_size():
            self.canvas.draw()
        self.set_motion_tooltip(
            on_hover, y=tooltip_y, x=tooltip_x, legend=tooltip_legend
        )
        self._schedule_figure_sync()

    def _save_figure(self, extension: str, file_filter: str) -> None:
        from activity_browser.bwutils.commontasks import savefilepath
        
        filepath = savefilepath(
            default_file_name=self.plot_name, file_filter=file_filter
        )
        if filepath:
            if not filepath.endswith(extension):
                filepath += extension
            self.figure.savefig(filepath)

    def to_png(self) -> None:
        self._save_figure(".png", self.PNG_FILTER)

    def to_svg(self) -> None:
        self._save_figure(".svg", self.SVG_FILTER)
