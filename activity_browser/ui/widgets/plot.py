import math

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from activity_browser.bwutils.commontasks import shorten_label, wrap_text


def widget_parent(node) -> object | None:
    """Next ancestor: Qt ``parent()`` or explicit ``.parent`` on analysis tabs."""
    if node is None:
        return None
    parent = getattr(node, "parent", None)
    if callable(parent):
        return parent()
    return parent


def lca_results_page_from_widget(widget) -> object | None:
    """Walk parents until :class:`LCAResultsPage` (plot widget or tab)."""
    node = widget
    while node is not None:
        if hasattr(node, "mlca") and hasattr(node, "cs_name"):
            return node
        node = widget_parent(node)
    return None


def lca_results_tab_from_widget(widget) -> object | None:
    """Walk parents until an LCA results sub-tab with per-tab plot display options."""
    node = widget
    while node is not None:
        if hasattr(node, "horizontal_bars") and hasattr(node, "full_labels"):
            parent = widget_parent(node)
            if parent is not None and hasattr(parent, "mlca"):
                return node
        node = widget_parent(node)
    return None


class ABFigureCanvas(FigureCanvasQTAgg):
    """Matplotlib's Qt canvas uses fig pixel size for :meth:`sizeHint`, so layouts and
    :class:`QScrollArea` grow the main window to match a wide figure. We only need the
    widget to fill the width given by the parent; :meth:`resizeEvent` on the base
    class already keeps the figure size in sync with the widget.
    """

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802 (Qt API)
        return QtCore.QSize(0, 0)

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(0, 0)


class ABPlot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    LABEL_COUNT_THRESHOLD = 8
    FONT_SIZE = 9
    LABEL_MAX_LENGTH = 40
    AXIS_LABEL_WRAP_LENGTH = 20
    # Vertical bar charts: horizontal tick labels; rotate 45° above this category count.
    CATEGORY_ROTATE_LABELS_ABOVE = 3
    # Horizontal bars: category labels sit on the y-axis and can use left margin width.
    HORIZONTAL_LABEL_WIDTH_FRACTION = 0.42
    HORIZONTAL_AXIS_LABEL_WRAP_LENGTH = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        # create figure, canvas, and axis
        self.figure = Figure(constrained_layout=True)
        self.canvas = ABFigureCanvas(self.figure)
        self.canvas.setMinimumHeight(0)
        self.canvas.setMinimumWidth(0)
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setMinimumWidth(0)

        self.ax = self.figure.add_subplot(111)  # create an axis
        self.plot_name = "Figure"
        self._hover_cid = None
        self._tooltip_y: list[str] = []
        self._tooltip_x: list[str] = []
        self._tooltip_legend: list[str] = []

        # Shared plot / tooltip context (bar rows = y categories, cols = series/containers).
        self.full_row_labels: list[str] = []
        self.full_col_labels: list[str] = []
        self.plot_unit: str | None = None
        self.plot_relative: bool = False
        self.col_scores: dict[str, float] = {}
        self.col_units: dict[str, str] = {}
        self._bar_values: np.ndarray | None = None
        self._bar_errors: np.ndarray | None = None
        self._hist_series: list[np.ndarray] = []

        self._set_plot_chrome_white()

        # set the layout
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

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802 (Qt API)
        sh = super().sizeHint()
        return QtCore.QSize(0, sh.height())

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        mh = super().minimumSizeHint()
        return QtCore.QSize(0, mh.height())

    def data_fontsize(self, item_count: int = 0) -> int:
        return self.FONT_SIZE

    def use_full_labels(self) -> bool:
        tab = lca_results_tab_from_widget(self)
        return bool(getattr(tab, "full_labels", False))

    def shorten_labels(self, labels: list[str], max_length: int | None = None) -> list[str]:
        if self.use_full_labels():
            return [str(label) for label in labels]
        ml = max_length or self.LABEL_MAX_LENGTH
        return [shorten_label(str(label), ml) for label in labels]

    def format_title(self, title: str, max_length: int | None = None) -> str:
        """Subplot / chart title (same wrap/ellipsis rules as category tick labels)."""
        ml = max_length or self.LABEL_MAX_LENGTH
        if self.use_full_labels():
            return self.wrap_labels_to_lines([str(title)], chars_per_line=ml, max_lines=3)[0]
        return shorten_label(str(title), ml)

    def legend_labels(self, labels: list[str], max_length: int | None = None) -> list[str]:
        """Legend entries: always wrap (e.g. 40 chars/line) to limit legend width."""
        ml = max_length or self.LABEL_MAX_LENGTH
        if self.use_full_labels():
            return [wrap_text(str(label), max_length=ml) for label in labels]
        return [shorten_label(str(label), ml) for label in labels]

    def wrap_labels(self, labels: list[str], max_length: int | None = None) -> list[str]:
        if self.use_full_labels():
            ml = max_length or self.LABEL_MAX_LENGTH
        else:
            ml = max_length or self.AXIS_LABEL_WRAP_LENGTH
        return [wrap_text(str(label), max_length=ml) for label in labels]

    @staticmethod
    def label_needs_tooltip(display: str, full: str) -> bool:
        """True when the on-chart label does not show the complete text."""
        display_n = str(display).strip()
        full_n = str(full).strip()
        if not full_n:
            return False
        if display_n == full_n:
            return False
        if "…" in display_n or "..." in display_n:
            return True
        if "\n" in display_n:
            return True
        return display_n != full_n

    def wrap_labels_to_lines(
        self,
        labels: list[str],
        *,
        chars_per_line: int,
        max_lines: int = 3,
    ) -> list[str]:
        """Wrap tick labels; truncate the last line with ``…`` when exceeding ``max_lines``."""
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

    @staticmethod
    def _single_line_label(label: str) -> str:
        return " ".join(str(label).split())

    def display_category_labels(
        self,
        labels: list[str],
        *,
        horizontal: bool = False,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
        rotate_above: int | None = None,
    ) -> tuple[list[str], bool]:
        """Unified wrapped category-axis labels; returns ``(display, use_rotation)``."""
        n_groups = len(labels)
        if n_groups == 0:
            return [], False
        threshold = (
            rotate_above
            if rotate_above is not None
            else self.CATEGORY_ROTATE_LABELS_ABOVE
        )
        use_rotation = not horizontal and n_groups > threshold
        chars_per_line = self.tick_label_chars_per_line(
            n_groups,
            grid_ncols=grid_ncols,
            legend_width_ratio=legend_width_ratio,
            horizontal=horizontal,
        )
        if use_rotation and self.use_full_labels():
            wrap_width = self.LABEL_MAX_LENGTH
            display = [
                wrap_text(self._single_line_label(label), max_length=wrap_width)
                for label in labels
            ]
            return display, True

        max_lines = 4 if horizontal else 3
        wrap_width = max(chars_per_line, 18) if use_rotation else chars_per_line
        display = self.wrap_labels_to_lines(
            labels, chars_per_line=wrap_width, max_lines=max_lines
        )
        return display, use_rotation

    def tick_label_chars_per_line(
        self,
        n_ticks: int,
        *,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
        horizontal: bool = False,
    ) -> int:
        """Estimate characters per line from viewport width and tick count."""
        width_in, _ = self.get_canvas_size_in_inches()
        if width_in < 2:
            width_in = 6.0
        ncols = max(grid_ncols, 1)
        total_ratio = ncols + max(legend_width_ratio, 0.0)
        panel_width_in = width_in * (1.0 / total_ratio)
        if horizontal:
            label_width_in = panel_width_in * self.HORIZONTAL_LABEL_WIDTH_FRACTION
            chars = max(12, int(label_width_in / 0.085))
            cap = self.HORIZONTAL_AXIS_LABEL_WRAP_LENGTH
            if self.use_full_labels():
                cap = max(cap, self.LABEL_MAX_LENGTH)
            return min(chars, cap)
        slot_in = panel_width_in / max(n_ticks, 1)
        chars = max(5, int(slot_in / 0.085))
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
        """Category-axis tick labels for grouped / stacked bar charts.

        Vertical bars: horizontal labels with width-aware wrapping when there are at most
        ``rotate_above`` categories; 45° rotation when there are more.
        Horizontal bars: wrapped labels on the y-axis (no rotation).
        """
        if not group_labels:
            return

        axis = "y" if horizontal else "x"
        display, use_rotation = self.display_category_labels(
            group_labels,
            horizontal=horizontal,
            grid_ncols=grid_ncols,
            legend_width_ratio=legend_width_ratio,
            rotate_above=rotate_above,
        )

        tick_size = self.FONT_SIZE
        if use_rotation:
            if axis == "x":
                ax.set_xticklabels(
                    display,
                    ha="right",
                    rotation=45,
                    rotation_mode="anchor",
                    fontsize=tick_size,
                )
                ax.tick_params(axis="x", pad=2)
            else:
                ax.set_yticklabels(
                    display,
                    ha="right",
                    rotation=45,
                    rotation_mode="anchor",
                    fontsize=tick_size,
                )
                ax.tick_params(axis="y", pad=2)
        else:
            if axis == "x":
                ax.set_xticklabels(
                    display,
                    ha="center",
                    rotation=0,
                    rotation_mode="default",
                    fontsize=tick_size,
                )
                ax.tick_params(axis="x", pad=2)
            else:
                ax.set_yticklabels(
                    display,
                    ha="right",
                    rotation=0,
                    rotation_mode="default",
                    fontsize=tick_size,
                )
                ax.tick_params(axis="y", pad=2)

    def wrapped_label_line_count(self, labels: list[str], max_length: int | None = None) -> int:
        wrapped = self.wrap_labels(labels, max_length=max_length)
        return max((text.count("\n") + 1 for text in wrapped), default=1)

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
        self.plot_unit = unit
        self.plot_relative = relative
        self.full_row_labels = list(row_labels) if row_labels else []
        self.full_col_labels = list(col_labels) if col_labels else []
        self._bar_values = bar_values
        self._bar_errors = bar_errors
        self.col_scores = dict(col_scores) if col_scores else {}
        self.col_units = dict(col_units) if col_units else {}
        self._hist_series = list(hist_series) if hist_series else []

    def apply_axis_fonts(self, ax) -> None:
        """Apply the standard plot font size to one axes (and its title/labels)."""
        size = self.FONT_SIZE
        for label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
            label.set_fontsize(size)
        if ax.xaxis.label:
            ax.xaxis.label.set_fontsize(size)
        if ax.yaxis.label:
            ax.yaxis.label.set_fontsize(size)
        if ax.title:
            ax.title.set_fontsize(size)

    def apply_standard_fonts(self, item_count: int) -> None:
        if self.ax is None:
            return
        self.apply_axis_fonts(self.ax)

    @staticmethod
    def compose_bar_tooltip(header_lines: list[str], value_lines: list[str]) -> str:
        """Join label header line(s) and value line(s) for hover tooltips."""
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
        """Primary value line(s); absolute LCA score or relative share on the last line."""
        if relative:
            if relative_already_percent:
                lines = [f"{value:.1f}%"]
            else:
                lines = [f"{100.0 * value:.1f}%"]
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
        bar = self.full_row_labels[bar_idx] if bar_idx < len(self.full_row_labels) else ""
        series = self.full_col_labels[series_idx] if series_idx < len(self.full_col_labels) else ""
        unit = self.col_units.get(bar) if self.col_units else self.plot_unit
        share_pct = None
        if not self.plot_relative:
            if score := self.col_scores.get(bar):
                share_pct = 100.0 * value / score
        value_lines = self.tooltip_value_lines(
            value,
            relative=self.plot_relative,
            unit=unit,
            relative_share_percent=share_pct,
        )
        if len(self.full_col_labels) > 1 and series:
            return self.compose_bar_tooltip([series, bar], value_lines)
        return self.compose_bar_tooltip([bar], value_lines)

    @staticmethod
    def _bar_patch_containers(ax):
        """Yield ``(patches,)`` for bar series, skipping error-bar-only containers."""
        for container in ax.containers:
            patches = getattr(container, "patches", None)
            if patches:
                yield patches

    def bar_patch_tooltip(self, event) -> str | None:
        if self._bar_values is None or event.inaxes is not self.ax:
            return None
        for series_idx, patches in enumerate(self._bar_patch_containers(self.ax)):
            for bar_idx, patch in enumerate(patches):
                inside, _ = patch.contains(event)
                if not inside:
                    continue
                if (
                    series_idx >= self._bar_values.shape[0]
                    or bar_idx >= self._bar_values.shape[1]
                ):
                    continue
                value = float(self._bar_values[series_idx, bar_idx])
                if np.isnan(value):
                    return None
                return self.format_bar_tooltip(series_idx, bar_idx, value)
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

    def _device_pixel_ratio(self) -> float:
        if hasattr(self.canvas, "devicePixelRatioF"):
            return float(self.canvas.devicePixelRatioF())
        return float(self.canvas.devicePixelRatio())

    def _qt_physical_pixel_size(self) -> tuple[float, float]:
        """Device pixels allocated to the plot (matches matplotlib's Qt :meth:`resizeEvent`)."""
        dpr = self._device_pixel_ratio()
        cw = max(self.canvas.width(), self.width(), 1)
        ch = max(self.canvas.height(), self.height(), 1)
        return cw * dpr, ch * dpr

    def get_canvas_size_in_inches(self) -> tuple[float, float]:
        """Figure size must follow **Qt layout**, not :meth:`~matplotlib.backends.backend_agg.FigureCanvasAgg.get_width_height` (figure buffer), or scroll areas widen the window."""
        w_px, h_px = self._qt_physical_pixel_size()
        dpi = self.figure.dpi
        return (w_px / dpi, h_px / dpi)

    def sync_figure_to_widget(self) -> None:
        """Resize the figure to the drawable area the layout assigned (no ``forward`` resize of Qt)."""
        w_px, h_px = self._qt_physical_pixel_size()
        dpr = self._device_pixel_ratio()
        # After plot(), the canvas may not yet reflect setMinimumHeight(); don't squash tall figures.
        min_h = self.minimumHeight()
        if min_h > 0:
            h_px = max(h_px, float(min_h) * dpr)
        w_px = max(w_px, 1.0)
        h_px = max(h_px, 1.0)
        dpi = self.figure.dpi
        self.figure.set_size_inches(w_px / dpi, h_px / dpi, forward=False)
        self.canvas.draw_idle()

    def _schedule_figure_sync(self) -> None:
        """After ``plot()`` the widget often has not been laid out yet; sync on next event-loop tick."""
        QtCore.QTimer.singleShot(0, self.sync_figure_to_widget)

    def set_minimum_height_for_figure_inches(self, height_inches: float) -> None:
        """Minimum Qt height (logical px) so tall figures scroll inside :class:`QScrollArea`."""
        phy_px = height_inches * self.figure.dpi
        logical = max(int(math.ceil(phy_px / self._device_pixel_ratio())), 1)
        self.setMinimumHeight(logical)

    def reset_minimum_figure_height(self) -> None:
        """Let the matplotlib figure follow the Qt layout instead of exceeding it."""
        self.setMinimumHeight(0)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_figure_sync()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        # Keep matplotlib canvas synced when splitters/window are resized (incl. maximize).
        self._schedule_figure_sync()

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def _set_plot_chrome_white(self) -> None:
        """Match figure and Qt canvas to the plot area so default grey margins disappear."""
        self.figure.patch.set_facecolor("white")
        if self.ax is not None:
            self.ax.set_facecolor("white")
        bg = "background-color: white;"
        self.canvas.setStyleSheet(bg)
        self.setStyleSheet(bg)

    def reset_plot(self) -> None:
        self.clear_hover_tooltip()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self._set_plot_chrome_white()

    def clear_hover_tooltip(self) -> None:
        if self._hover_cid is not None:
            self.canvas.mpl_disconnect(self._hover_cid)
            self._hover_cid = None
        QtWidgets.QToolTip.hideText()

    def _truncated_label_tooltip(self, event) -> str | None:
        """Full text for wrapped or shortened axis and legend labels."""
        if self.ax is None or event.x is None or event.y is None:
            return None
        renderer = self.figure.canvas.get_renderer()
        for ticks, full_labels in (
            (self.ax.get_yticklabels(), self._tooltip_y),
            (self.ax.get_xticklabels(), self._tooltip_x),
        ):
            if not full_labels:
                continue
            for tick, full in zip(ticks, full_labels):
                if self.label_needs_tooltip(
                    tick.get_text(), full
                ) and tick.get_window_extent(renderer).contains(event.x, event.y):
                    return full
        legend = self.ax.get_legend()
        if legend is not None and self._tooltip_legend:
            for text, full in zip(legend.get_texts(), self._tooltip_legend):
                if self.label_needs_tooltip(
                    text.get_text(), full
                ) and text.get_window_extent(renderer).contains(event.x, event.y):
                    return full
        return None

    def _data_hover_tooltip(self, event) -> str | None:
        if tip := self.bar_patch_tooltip(event):
            return tip
        return self.histogram_x_tooltip(event)

    def set_motion_tooltip(
        self,
        on_hover=None,
        *,
        y: list[str] | None = None,
        x: list[str] | None = None,
        legend: list[str] | None = None,
        offset: tuple[int, int] = (12, 12),
    ) -> None:
        """Qt tooltips for truncated labels and optional plot-specific hover text."""
        self._tooltip_y = list(y) if y else []
        self._tooltip_x = list(x) if x else []
        self._tooltip_legend = list(legend) if legend else []

        def tooltip_at_event(event):
            if tip := self._truncated_label_tooltip(event):
                return tip
            if tip := self._data_hover_tooltip(event):
                return tip
            if on_hover is not None:
                return on_hover(event)
            return None

        self.install_motion_tooltip(tooltip_at_event, offset=offset)

    def add_legend(self, *args, ax=None, **kwargs):
        """Legend with a single column (project-wide convention)."""
        kwargs.setdefault("ncol", 1)
        kwargs.setdefault("frameon", False)
        target = ax if ax is not None else self.ax
        return target.legend(*args, **kwargs)

    def finish_plot(
        self,
        item_count: int,
        *,
        on_hover=None,
        tooltip_y: list[str] | None = None,
        tooltip_x: list[str] | None = None,
        tooltip_legend: list[str] | None = None,
    ) -> None:
        self.apply_standard_fonts(item_count)
        self._set_plot_chrome_white()
        self.sync_figure_to_widget()
        w_px, h_px = self._qt_physical_pixel_size()
        if w_px >= 16 and h_px >= 16:
            self.canvas.draw()
        self.set_motion_tooltip(
            on_hover,
            y=tooltip_y,
            x=tooltip_x,
            legend=tooltip_legend,
        )
        self._schedule_figure_sync()

    def install_motion_tooltip(
        self, tooltip_at_event, *, offset: tuple[int, int] = (12, 12)
    ) -> None:
        """Show a Qt tooltip when ``tooltip_at_event(mpl_event)`` returns text."""
        self.clear_hover_tooltip()
        self.canvas.setMouseTracking(True)
        dx, dy = offset

        def on_motion(event):
            tip = tooltip_at_event(event)
            if tip:
                # Matplotlib event coords do not match Qt widget coords; follow the cursor.
                pos = QtGui.QCursor.pos() + QtCore.QPoint(dx, dy)
                QtWidgets.QToolTip.showText(pos, tip, self.canvas)
            else:
                QtWidgets.QToolTip.hideText()

        self._hover_cid = self.canvas.mpl_connect("motion_notify_event", on_motion)

    def to_png(self):
        """Export to .png format."""
        from activity_browser.bwutils.commontasks import savefilepath

        filepath = savefilepath(
            default_file_name=self.plot_name, file_filter=self.PNG_FILTER
        )
        if filepath:
            if not filepath.endswith(".png"):
                filepath += ".png"
            self.figure.savefig(filepath)

    def to_svg(self):
        """Export to .svg format."""
        from activity_browser.bwutils.commontasks import savefilepath

        filepath = savefilepath(
            default_file_name=self.plot_name, file_filter=self.SVG_FILTER
        )
        if filepath:
            if not filepath.endswith(".svg"):
                filepath += ".svg"
            self.figure.savefig(filepath)
