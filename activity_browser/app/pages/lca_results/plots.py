import math

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import seaborn as sns

import bw2data as bd
from bw2data import methods
from qtpy import QtCore
from activity_browser.ui.widgets import ABPlot
from activity_browser.ui.widgets.plot import lca_results_tab_from_widget
from activity_browser.bwutils.commontasks import (
    format_reference_flow_label,
    unit_of_method,
    wrap_text,
)
from activity_browser.bwutils.lcia_overview import (
    LCIAOverviewData,
    LCIAOverviewPanel,
)


def horizontal_bars_from_page(plot_widget) -> bool:
    """Per-tab ``horizontal_bars`` on the LCA results sub-tab owning the plot."""
    tab = lca_results_tab_from_widget(plot_widget)
    return bool(getattr(tab, "horizontal_bars", False))


def full_labels_from_page(plot_widget) -> bool:
    """Per-tab ``full_labels`` on the LCA results sub-tab owning the plot."""
    tab = lca_results_tab_from_widget(plot_widget)
    return bool(getattr(tab, "full_labels", False))


def contribution_series_colors(n: int) -> np.ndarray:
    """Distinct colors for stacked contribution series (one color per contributor)."""
    if n <= 0:
        return np.empty((0, 4))
    if n <= 10:
        return plt.cm.tab10(np.arange(n) % 10)
    if n <= 20:
        return plt.cm.tab20(np.arange(n) % 20)
    return plt.cm.hsv(np.linspace(0.05, 0.95, n, endpoint=False))


_CONTRIBUTION_SPECIAL_ROWS = frozenset({"Score", "Rest (+)", "Rest (-)"})


def contribution_row_labels(df: pd.DataFrame) -> list[str]:
    """Contributor labels using reference-flow formatting when keys are available."""
    if "index" not in df.columns:
        return [str(i).strip() for i in df.index]

    has_keys = "database" in df.columns and "code" in df.columns
    labels: list[str] = []
    for _, row in df.iterrows():
        text = str(row["index"]).strip()
        if text in _CONTRIBUTION_SPECIAL_ROWS or not has_keys:
            labels.append(text)
            continue
        db, code = row["database"], row["code"]
        if pd.isna(db) or pd.isna(code):
            labels.append(text)
            continue
        try:
            labels.append(format_reference_flow_label(bd.get_activity((db, code))))
        except Exception:
            labels.append(text)
    return labels


def contribution_column_labels(tab, column_names: list) -> list[str]:
    """Category-axis labels; reference flows when comparing impact categories."""
    names = [str(c).strip() for c in column_names]
    if tab is None or not hasattr(tab, "switches"):
        return names
    if tab.switches.currentIndex() != tab.switches.indexes.func:
        return names
    mlca = getattr(tab.parent, "mlca", None)
    if mlca is None:
        return names
    keys = list(mlca.fu_activity_keys)
    if len(keys) != len(names):
        return names
    try:
        return [format_reference_flow_label(bd.get_activity(k)) for k in keys]
    except Exception:
        return names


def contribution_row_colors(full_rows: list[str], display_rows: list[str]) -> list:
    """Map each contributor row to a color (stable order; grey for Rest rows)."""
    palette = contribution_series_colors(
        sum(
            1
            for full, disp in zip(full_rows, display_rows)
            if str(full).strip() not in ("Rest (+)", "Rest (-)")
            and str(disp).strip() not in ("Rest (+)", "Rest (-)")
        )
    )
    colors: list = []
    pal_i = 0
    for full, disp in zip(full_rows, display_rows):
        if str(full).strip() in ("Rest (+)", "Rest (-)") or str(disp).strip() in (
            "Rest (+)",
            "Rest (-)",
        ):
            colors.append([0.8, 0.8, 0.8, 1.0])
        else:
            colors.append(palette[pal_i])
            pal_i += 1
    return colors


def near_square_subplot_grid(n: int) -> tuple[int, int]:
    """Return ``(nrows, ncols)`` grid, as square as practical (e.g. 2×2, 2×3, 3×3)."""
    if n <= 0:
        return 0, 0
    best: tuple[tuple[int, int, int], int, int] | None = None
    for ncols in range(1, n + 1):
        nrows = math.ceil(n / ncols)
        aspect_diff = abs(ncols - nrows)
        spare = ncols * nrows - n
        landscape = 0 if ncols >= nrows else 1
        score = (aspect_diff, spare, landscape)
        if best is None or score < best[0]:
            best = (score, nrows, ncols)
    assert best is not None
    return best[1], best[2]


class LCIAResultsOverviewPlot(ABPlot):
    """Grouped bars for the LCIA landing tab (never stacked; vertical by default)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "LCA scores"
        self._overview: LCIAOverviewData | None = None
        self._panel: LCIAOverviewPanel | None = None
        self._relative = True
        self._horizontal = False
        self._panel_axes: list = []
        self._panel_contexts: list[dict] = []
        self._legend_ax = None

    def _configure_figure_layout(
        self,
        *,
        n_panels: int = 1,
        max_groups: int = 0,
    ) -> None:
        """Keep axes, tick labels, and legend inside the Qt viewport (``constrained_layout``)."""
        self.figure.set_constrained_layout(True)
        nrows, _ = near_square_subplot_grid(n_panels) if n_panels > 1 else (1, 1)
        use_rotation = (
            not self._horizontal
            and max_groups > self.CATEGORY_ROTATE_LABELS_ABOVE
        )
        if self._horizontal:
            w_pad, h_pad = 0.22, 0.06
        elif use_rotation:
            w_pad, h_pad = 0.04, 0.18
        else:
            w_pad, h_pad = 0.04, 0.08
        hspace = 0.14 if nrows > 1 else 0.08
        self.figure.set_constrained_layout_pads(
            w_pad=w_pad,
            h_pad=h_pad,
            hspace=hspace,
            wspace=0.08,
        )

    def _format_panel_bar_tooltip(
        self,
        panel: LCIAOverviewPanel,
        container_idx: int,
        category_idx: int,
        value: float,
    ) -> str:
        group = panel.group_labels[category_idx]
        series = panel.series_labels[container_idx]
        series_units = getattr(self._overview, "series_units", {}) or {}
        unit = panel.group_units.get(group, "") or series_units.get(series, "")
        absolute_value = None
        if self._relative:
            absolute_value = float(panel.absolute_values[category_idx, container_idx])
        value_lines = self.tooltip_value_lines(
            value,
            relative=self._relative,
            unit=unit,
            absolute_value=absolute_value,
            relative_already_percent=True,
        )
        if len(panel.series_labels) > 1:
            return self.compose_bar_tooltip([series, group], value_lines)
        return self.compose_bar_tooltip([group], value_lines)

    def format_bar_tooltip(self, container_idx: int, category_idx: int, value: float) -> str:
        if self._panel is not None:
            return self._format_panel_bar_tooltip(
                self._panel, container_idx, category_idx, value
            )
        if self._overview is None:
            return ""
        panel = LCIAOverviewPanel(
            title="",
            values=self._overview.values,
            absolute_values=self._overview.absolute_values,
            group_labels=self._overview.group_labels,
            series_labels=self._overview.series_labels,
            group_units=self._overview.group_units,
            y_label=self._overview.y_label,
        )
        return self._format_panel_bar_tooltip(
            panel, container_idx, category_idx, value
        )

    def bar_patch_tooltip(self, event) -> str | None:
        if self._panel_contexts:
            if event.inaxes is None:
                return None
            for ctx in self._panel_contexts:
                if event.inaxes is not ctx["ax"]:
                    continue
                bar_values = ctx["bar_values"]
                ax = ctx["ax"]
                for series_idx, container in enumerate(ax.containers):
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
                        return self._format_panel_bar_tooltip(
                            ctx["panel"], series_idx, bar_idx, value
                        )
            return None
        return super().bar_patch_tooltip(event)

    def _truncated_label_tooltip(self, event) -> str | None:
        if not self._panel_contexts:
            return super()._truncated_label_tooltip(event)
        if event.x is None or event.y is None:
            return None
        renderer = self.figure.canvas.get_renderer()
        for ctx in self._panel_contexts:
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
                    ) and tick.get_window_extent(renderer).contains(
                        event.x, event.y
                    ):
                        return full
            full_title = ctx.get("full_title") or ""
            title_artist = ax.title
            if full_title and self.label_needs_tooltip(
                title_artist.get_text(), full_title
            ) and title_artist.get_window_extent(renderer).contains(
                event.x, event.y
            ):
                return full_title
        legend = self._legend_ax.get_legend() if self._legend_ax is not None else None
        if legend is not None and self._tooltip_legend:
            for text, full in zip(legend.get_texts(), self._tooltip_legend):
                if self.label_needs_tooltip(
                    text.get_text(), full
                ) and text.get_window_extent(renderer).contains(event.x, event.y):
                    return full
        return None

    def apply_standard_fonts(self, item_count: int) -> None:
        for ax in self._panel_axes or ([self.ax] if self.ax is not None else []):
            self.apply_axis_fonts(ax)
        for legend in self.figure.legends:
            for text in legend.get_texts():
                text.set_fontsize(self.FONT_SIZE)

    def _draw_panel(
        self,
        ax,
        panel: LCIAOverviewPanel,
        *,
        relative: bool,
        horizontal: bool = False,
        show_ylabel: bool = True,
        show_legend: bool = True,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
    ) -> tuple[list[str], int, int]:
        n_groups = len(panel.group_labels)
        n_series = len(panel.series_labels)
        if n_groups == 0 or n_series == 0:
            return [], 0, 0

        categories = np.arange(n_groups)
        group_width = min(0.9, 0.15 * n_series * n_groups)
        bar_thickness = group_width / max(n_series, 1)
        cmap = plt.cm.tab10(np.linspace(0, 1, max(n_series, 1)))
        series_legend = self.legend_labels(panel.series_labels)

        for s_idx in range(n_series):
            offsets = (
                categories
                - group_width / 2
                + bar_thickness / 2
                + s_idx * bar_thickness
            )
            heights = panel.values[:, s_idx]
            color = cmap[s_idx % len(cmap)]
            colors = [color] * len(heights)
            if horizontal:
                ax.barh(
                    offsets,
                    heights,
                    height=bar_thickness * 0.92,
                    label=series_legend[s_idx],
                    color=colors,
                    edgecolor="white",
                    linewidth=0.3,
                )
            else:
                ax.bar(
                    offsets,
                    heights,
                    width=bar_thickness * 0.92,
                    label=series_legend[s_idx],
                    color=colors,
                    edgecolor="white",
                    linewidth=0.3,
                )

        if horizontal:
            ax.set_yticks(categories)
            ax.invert_yaxis()
        else:
            ax.set_xticks(categories)
        self._set_category_ticklabels(
            ax,
            panel.group_labels,
            horizontal=horizontal,
            grid_ncols=grid_ncols,
            legend_width_ratio=legend_width_ratio,
        )
        if show_ylabel and panel.y_label:
            if horizontal:
                ax.set_xlabel(panel.y_label, fontsize=self.FONT_SIZE)
            else:
                ax.set_ylabel(panel.y_label, fontsize=self.FONT_SIZE)
        if horizontal:
            ax.axvline(0, color="black", linewidth=0.8, zorder=1)
            ax.grid(axis="x", linestyle="dashed", color="grey", alpha=0.7)
        else:
            ax.axhline(0, color="black", linewidth=0.8, zorder=1)
            ax.grid(axis="y", linestyle="dashed", color="grey", alpha=0.7)
        ax.set_axisbelow(True)

        if show_legend and n_series >= 1:
            self.add_legend(
                loc="upper left",
                bbox_to_anchor=(1.02, 1),
                fontsize=self.FONT_SIZE,
                ax=ax,
            )
        self.apply_axis_fonts(ax)
        return panel.group_labels, n_groups, n_series

    def plot(
        self,
        data: LCIAOverviewData,
        *,
        relative: bool = True,
        horizontal: bool = False,
    ) -> None:
        self.reset_plot()
        self._overview = data
        self._panel = None
        self._panel_axes = []
        self._panel_contexts = []
        self._legend_ax = None
        self._relative = relative
        self._horizontal = horizontal
        self.reset_minimum_figure_height()

        if data.panels:
            self._plot_panels(
                data,
                relative=relative,
                horizontal=horizontal,
            )
            return

        n_groups = len(data.group_labels)
        n_series = len(data.series_labels)
        if n_groups == 0 or n_series == 0:
            self.canvas.draw()
            return

        self._configure_figure_layout(n_panels=1, max_groups=n_groups)

        panel = LCIAOverviewPanel(
            title="",
            values=data.values,
            absolute_values=data.absolute_values,
            group_labels=data.group_labels,
            series_labels=data.series_labels,
            group_units=data.group_units,
            y_label=data.y_label,
        )
        self._panel = panel
        group_labels, _, _ = self._draw_panel(
            self.ax,
            panel,
            relative=relative,
            horizontal=horizontal,
        )

        bar_values = data.values.T
        self.set_plot_context(
            relative=relative,
            row_labels=data.group_labels,
            col_labels=data.series_labels,
            bar_values=bar_values,
        )
        self.finish_plot(
            max(n_groups, n_series),
            tooltip_x=None if horizontal else group_labels,
            tooltip_y=group_labels if horizontal else None,
            tooltip_legend=data.series_labels if n_series >= 1 else None,
        )

    def _legend_column_width_ratio(self) -> float:
        """GridSpec width for the legend column (~``LABEL_MAX_LENGTH`` characters)."""
        ratio = self.LABEL_MAX_LENGTH / 160.0
        return max(0.12, min(0.4, ratio))

    def _plot_panels(
        self,
        data: LCIAOverviewData,
        *,
        relative: bool,
        horizontal: bool,
    ) -> None:
        panels = data.panels
        n_panels = len(panels)
        nrows, ncols = near_square_subplot_grid(n_panels)

        self.figure.clf()

        legend_ratio = self._legend_column_width_ratio()
        self._grid_ncols = ncols
        self._legend_width_ratio = legend_ratio
        gs = GridSpec(
            nrows,
            ncols + 1,
            figure=self.figure,
            width_ratios=[1.0] * ncols + [legend_ratio],
        )

        self._panel_axes = []
        self._panel_contexts = []
        self._legend_ax = None
        first_ax = None
        first_group_labels: list[str] = []
        max_items = 0
        legend_labels: list[str] = []
        for idx, panel in enumerate(panels):
            row, col = divmod(idx, ncols)
            ax = self.figure.add_subplot(gs[row, col])
            self._panel_axes.append(ax)
            if first_ax is None:
                first_ax = ax
            group_labels, n_groups, n_series = self._draw_panel(
                ax,
                panel,
                relative=relative,
                horizontal=horizontal,
                show_ylabel=True,
                show_legend=False,
                grid_ncols=ncols,
                legend_width_ratio=legend_ratio,
            )
            ax.set_title(
                self.format_title(panel.title),
                fontsize=self.FONT_SIZE,
            )
            self._panel_contexts.append(
                {
                    "ax": ax,
                    "panel": panel,
                    "bar_values": panel.values.T,
                    "full_title": panel.title,
                    "tooltip_x": None if horizontal else group_labels,
                    "tooltip_y": group_labels if horizontal else None,
                }
            )
            if idx == 0:
                first_group_labels = group_labels
                legend_labels = panel.series_labels
            max_items = max(max_items, n_groups, n_series)

        for idx in range(n_panels, nrows * ncols):
            row, col = divmod(idx, ncols)
            ax = self.figure.add_subplot(gs[row, col])
            ax.set_visible(False)

        if first_ax is not None and legend_labels:
            legend_ax = self.figure.add_subplot(gs[:, ncols])
            self._legend_ax = legend_ax
            legend_ax.axis("off")
            handles, _ = first_ax.get_legend_handles_labels()
            wrapped_legend = self.legend_labels(legend_labels)
            legend = legend_ax.legend(
                handles,
                wrapped_legend,
                loc="center left",
                fontsize=self.FONT_SIZE,
                frameon=False,
                ncol=1,
                borderaxespad=0,
                handlelength=1.2,
                handletextpad=0.5,
            )
            for text in legend.get_texts():
                text.set_fontsize(self.FONT_SIZE)

        self._configure_figure_layout(n_panels=n_panels, max_groups=max_items)

        self.ax = first_ax if first_ax is not None else self.figure.add_subplot(111)
        self._panel = panels[0] if panels else None
        if panels:
            self.set_plot_context(
                relative=relative,
                row_labels=panels[0].group_labels,
                col_labels=panels[0].series_labels,
                bar_values=panels[0].values.T,
            )
        self.reset_minimum_figure_height()
        self.finish_plot(
            max_items,
            tooltip_x=None if horizontal else first_group_labels,
            tooltip_y=first_group_labels if horizontal else None,
            tooltip_legend=legend_labels if legend_labels else None,
        )


class LCAResultsBarChart(ABPlot):
    """Generate a bar chart comparing the absolute LCA scores of the products."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "LCA scores"

    def plot(self, df: pd.DataFrame, method: tuple, labels: list):
        self.reset_plot()
        width_inches, height_inches = self.get_canvas_size_in_inches()
        self.figure.set_size_inches(width_inches, height_inches, forward=False)

        full_y = [str(label) for label in labels]
        unit = methods[method].get("unit")

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/489
        df = df.copy()
        df.index = pd.Index(range(len(full_y)))
        show_legend = df.shape[1] != 1
        df.plot.barh(ax=self.ax, legend=False)
        self.ax.invert_yaxis()
        self.ax.set_yticks(np.arange(len(full_y)))
        self._set_category_ticklabels(
            self.ax, full_y, horizontal=True, legend_width_ratio=0.18 if show_legend else 0.0
        )
        if show_legend:
            handles, _ = self.ax.get_legend_handles_labels()
            col_full = [str(c) for c in df.columns]
            self.add_legend(
                handles,
                self.legend_labels(col_full),
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                fontsize=self.FONT_SIZE,
            )
        self.ax.set_xlabel(unit)

        self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
        self.ax.set_axisbelow(True)

        values = df.to_numpy(dtype=float).T
        self.set_plot_context(
            unit=unit,
            row_labels=full_y,
            col_labels=[str(c) for c in df.columns],
            bar_values=values,
        )
        self.finish_plot(
            len(labels),
            tooltip_y=full_y,
            tooltip_legend=[str(c) for c in df.columns] if show_legend else None,
        )


class ContributionPlot(ABPlot):
    MAX_LEGEND = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Contributions"
        self.parent = parent

    def format_bar_tooltip(self, container_idx: int, category_idx: int, value: float) -> str:
        contributor = self.full_row_labels[container_idx]
        col = self.full_col_labels[category_idx]
        unit = self.col_units.get(col) if self.col_units else self.plot_unit
        share_pct = None
        if not self.plot_relative:
            if score := self.col_scores.get(col):
                share_pct = 100.0 * value / score
        value_lines = self.tooltip_value_lines(
            value,
            relative=self.plot_relative,
            unit=unit,
            relative_share_percent=share_pct,
            relative_already_percent=self.plot_relative,
        )
        header = [contributor]
        if len(self.full_col_labels) > 1 and col:
            header = [col, contributor]
        return self.compose_bar_tooltip(header, value_lines)

    def plot(self, df: pd.DataFrame, unit: str = None):
        """Plot a stacked bar chart of contributions (vertical by default)."""
        horizontal = horizontal_bars_from_page(self)
        dfp = df.copy()
        full_rows = contribution_row_labels(dfp)
        dfp.index = full_rows
        relative = bool(getattr(self.parent, "relative", False))
        col_scores: dict[str, float] = {}
        col_units: dict[str, str] = {}
        tab = self.parent
        if not relative and tab.switches.currentIndex() == tab.switches.indexes.method:
            contributions = tab.parent.contributions
            for method in tab.parent.mlca.methods:
                u = unit_of_method(method)
                col_units[contributions.get_labels([method])[0].strip()] = u
                col_units[" | ".join(list(method))] = u

        value_cols = list(dfp.select_dtypes(include=np.number).columns)
        full_cols = contribution_column_labels(self.parent, value_cols)

        if not relative and "Score" in dfp.index:
            score = dfp.loc["Score"]
            for raw_col, label in zip(value_cols, full_cols):
                if pd.notna(score.get(raw_col)):
                    col_scores[label] = float(score[raw_col])

        dfp.drop(dfp.select_dtypes(["object"]), axis=1, inplace=True)
        if "Score" in dfp.index:
            dfp.drop("Score", inplace=True)
        rows_to_drop = dfp.index[
            (dfp == 0).all(axis=1) & ~dfp.index.isin(["Rest (+)", "Rest (-)"])
        ]
        dfp = dfp.drop(rows_to_drop)
        full_rows = [str(i).strip() for i in dfp.index]

        dfp = dfp[value_cols]
        dfp.columns = full_cols
        bar_values = dfp.to_numpy(dtype=float)

        self.ax.clear()
        canvas_width_inches, _ = self.get_canvas_size_in_inches()
        optimal_height_inches = 4 + dfp.shape[1] * 0.55
        if not horizontal:
            canvas_width_inches = max(canvas_width_inches, 0.45 * dfp.shape[1], 4.0)
        self.figure.set_size_inches(
            canvas_width_inches, optimal_height_inches, forward=False
        )

        display_rows = self.shorten_labels(full_rows)
        dfp.index = pd.Index(display_rows)
        dfp.columns = pd.Index(self.shorten_labels(full_cols))

        row_colors = contribution_row_colors(full_rows, display_rows)

        show_legend = dfp.shape[0] < self.MAX_LEGEND
        plot_df = dfp.T
        if horizontal:
            plot_df.plot.barh(
                stacked=True,
                color=row_colors,
                ax=self.ax,
                legend=False,
            )
            self.ax.invert_yaxis()
            self._set_category_ticklabels(
                self.ax,
                full_cols,
                horizontal=True,
                legend_width_ratio=0.18 if show_legend else 0.0,
            )
            if unit:
                self.ax.set_xlabel(unit)
            self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
            self.ax.axvline(0, color="black", linewidth=0.8, zorder=1)
        else:
            plot_df.plot.bar(
                stacked=True,
                color=row_colors,
                ax=self.ax,
                legend=False,
            )
            if unit:
                self.ax.set_ylabel(unit)
            self.ax.grid(which="major", axis="y", color="grey", linestyle="dashed")
            self.ax.axhline(0, color="black", linewidth=0.8, zorder=1)
            self._set_category_ticklabels(
                self.ax,
                full_cols,
                horizontal=False,
                legend_width_ratio=0.18 if show_legend else 0.0,
            )

        self.ax.set_axisbelow(True)

        if show_legend:
            handles, _ = self.ax.get_legend_handles_labels()
            if not handles:
                handles = [
                    container.patches[0]
                    for container in self.ax.containers
                    if container.patches
                ]
            self.add_legend(
                handles,
                self.legend_labels(full_rows),
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                fontsize=self.data_fontsize(dfp.shape[0]),
            )

        marker_size = max(min(150 / dfp.shape[1], 35), 10)
        for i in range(dfp.shape[1]):
            s = dfp.iloc[:, i]
            total = float(s.sum())
            abs_total = float(s.abs().sum())
            if not math.isclose(abs(total), abs_total, rel_tol=1e-9, abs_tol=1e-15):
                if horizontal:
                    self.ax.plot(
                        total,
                        i,
                        markersize=marker_size,
                        marker="d",
                        fillstyle="left",
                        markerfacecolor="black",
                        markerfacecoloralt="grey",
                        markeredgecolor="white",
                    )
                else:
                    self.ax.plot(
                        i,
                        total,
                        markersize=marker_size,
                        marker="d",
                        fillstyle="left",
                        markerfacecolor="black",
                        markerfacecoloralt="grey",
                        markeredgecolor="white",
                    )

        self.set_plot_context(
            unit=unit,
            relative=relative,
            row_labels=full_rows,
            col_labels=full_cols,
            bar_values=bar_values,
            col_scores=col_scores,
            col_units=col_units,
        )
        self.set_minimum_height_for_figure_inches(optimal_height_inches)
        self.finish_plot(
            max(dfp.shape),
            tooltip_x=None if horizontal else full_cols,
            tooltip_y=full_cols if horizontal else None,
            tooltip_legend=full_rows if show_legend else None,
        )


class CorrelationPlot(ABPlot):
    def __init__(self, parent=None):
        super().__init__(parent)
        sns.set(style="darkgrid")

    def plot(self, df: pd.DataFrame):
        """Plot a heatmap of correlations between different reference flows."""
        self.reset_plot()
        canvas_width_inches, _ = self.get_canvas_size_in_inches()
        height_inches = 4 + df.shape[1] * 0.3
        self.figure.set_size_inches(canvas_width_inches, height_inches, forward=False)

        corr = df.corr()
        mask = np.zeros_like(corr, dtype=bool)
        mask[np.triu_indices_from(mask)] = True
        vmax = np.abs(corr.values[~mask]).max()
        sns.heatmap(
            corr,
            mask=mask,
            cmap=plt.cm.PuOr,
            vmin=-vmax,
            vmax=vmax,
            square=True,
            linecolor="lightgray",
            linewidths=1,
            ax=self.ax,
        )

        text_size = self.data_fontsize(df.shape[1])
        upright = df.shape[1] <= self.LABEL_COUNT_THRESHOLD
        for i in range(len(corr)):
            self.ax.text(
                i + 0.5,
                i + 0.5,
                corr.columns[i],
                ha="center",
                va="center",
                rotation=0 if upright else 45,
                size=text_size,
            )
            for j in range(i + 1, len(corr)):
                self.ax.text(
                    j + 0.5,
                    i + 0.5,
                    f"{corr.values[i, j]:.3f}",
                    ha="center",
                    va="center",
                    rotation=0 if upright else 45,
                    size=text_size,
                )
        self.ax.axis("off")

        self.set_minimum_height_for_figure_inches(height_inches)
        self.finish_plot(df.shape[1])


class MonteCarloPlot(ABPlot):
    """Monte Carlo plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Monte Carlo"

    def plot(self, df: pd.DataFrame, method: tuple):
        self.ax.clear()
        n_series = df.shape[1]
        unit = methods[method]["unit"]
        legend_full = [str(c) for c in df.columns]
        hist_series: list[np.ndarray] = []

        for j in range(n_series):
            series = df.iloc[:, j]
            vals = np.ravel(np.asarray(series.dropna(), dtype=float))
            hist_series.append(vals)
            if vals.size == 0:
                continue
            color = self.ax._get_lines.get_next_color()
            label = self.legend_labels([legend_full[j]])[0]
            self.ax.hist(
                vals,
                density=True,
                alpha=0.5,
                label=label,
                color=color,
            )
            self.ax.axvline(float(np.mean(vals)), color=color)

        self.ax.set_xlabel(unit)
        self.ax.set_ylabel("Probability")

        if n_series:
            self.add_legend(
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                fontsize=self.data_fontsize(n_series),
            )

        height_inches = max(4.0, 3.5 + min(n_series, 20) * 0.12)
        self.set_minimum_height_for_figure_inches(height_inches)

        self.set_plot_context(
            unit=unit,
            col_labels=legend_full,
            hist_series=hist_series,
        )
        self.finish_plot(
            n_series,
            tooltip_legend=legend_full if n_series else None,
        )


GSA_TYPE_COLORS = {
    "technosphere": "#1f77b4",
    "biosphere": "#2ca02c",
    "characterization factor": "#ff7f0e",
    "parameter": "#9467bd",
}


class GSAPlot(ABPlot):
    """Bar chart of SALib delta indices with ``delta_conf`` error bars (vertical by default)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "GSA"
        self._plot_df: pd.DataFrame | None = None
        self._max_rows = 10

    def format_bar_tooltip(self, container_idx: int, category_idx: int, value: float) -> str:
        name = self.full_row_labels[category_idx]
        value_line = f"δ = {value:,.4g}"
        if self._bar_errors is not None:
            err = float(self._bar_errors[container_idx, category_idx])
            if not np.isnan(err):
                value_line += f" ± {err:,.4g}"
        return self.compose_bar_tooltip([name], [value_line])

    def plot(self, df: pd.DataFrame, max_rows: int = 10):
        self._plot_df = df
        self._max_rows = max_rows
        self._render()

    def _render(self) -> None:
        from activity_browser.bwutils.sensitivity_analysis import GSA_NAME_COLUMN, GSA_TYPE_COLUMN

        df = self._plot_df
        if df is None:
            return

        self.setMinimumHeight(0)
        self.reset_plot()

        dfp = df.dropna(subset=["delta", "delta_conf"]).head(max(1, int(self._max_rows))).copy()
        if dfp.empty:
            self.canvas.draw()
            self._schedule_figure_sync()
            return

        width_inches, height_inches = self.get_canvas_size_in_inches()
        if width_inches < 2:
            width_inches = 6.0
        if height_inches < 2:
            height_inches = 4.0
        self.figure.set_size_inches(width_inches, height_inches, forward=False)

        horizontal = horizontal_bars_from_page(self)
        n = len(dfp)
        positions = np.arange(n)
        deltas = dfp["delta"].to_numpy(dtype=float)
        conf = dfp["delta_conf"].to_numpy(dtype=float)
        colors = [GSA_TYPE_COLORS.get(t, "#7f7f7f") for t in dfp[GSA_TYPE_COLUMN]]
        full_y = [str(name) for name in dfp[GSA_NAME_COLUMN]]
        handles = [
            Patch(color=GSA_TYPE_COLORS.get(gsa_type, "#7f7f7f"), label=gsa_type)
            for gsa_type in dfp[GSA_TYPE_COLUMN].drop_duplicates()
        ]
        legend_width_ratio = 0.18 if handles else 0.0

        if horizontal:
            self.ax.barh(
                positions,
                deltas,
                xerr=conf,
                color=colors,
                capsize=3,
                ecolor="#333333",
                height=0.75,
            )
            self.ax.set_yticks(positions)
            self.ax.invert_yaxis()
            self._set_category_ticklabels(
                self.ax,
                full_y,
                horizontal=True,
                legend_width_ratio=legend_width_ratio,
            )
            self.ax.set_xlabel("Delta sensitivity index")
            self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
            self.ax.tick_params(axis="y", length=0)
        else:
            self.ax.bar(
                positions,
                deltas,
                yerr=conf,
                color=colors,
                capsize=3,
                ecolor="#333333",
                width=0.75,
            )
            self.ax.set_xticks(positions)
            self._set_category_ticklabels(
                self.ax,
                full_y,
                horizontal=False,
                legend_width_ratio=legend_width_ratio,
            )
            self.ax.set_ylabel("Delta sensitivity index")
            self.ax.grid(which="major", axis="y", color="grey", linestyle="dashed")
            self.ax.tick_params(axis="x", length=0)
        self.ax.set_axisbelow(True)

        if handles:
            self.figure.set_constrained_layout(True)
            self.figure.set_constrained_layout_pads(w_pad=0.14, h_pad=0.06)
            self.add_legend(
                handles=handles,
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                fontsize=self.data_fontsize(len(handles)),
            )

        values = deltas.reshape(1, -1)
        errors = conf.reshape(1, -1)
        self.set_plot_context(
            row_labels=full_y,
            bar_values=values,
            bar_errors=errors,
        )
        self.finish_plot(
            n,
            tooltip_y=full_y if horizontal else None,
            tooltip_x=full_y if not horizontal else None,
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._plot_df is not None and not self._plot_df.empty:
            QtCore.QTimer.singleShot(0, self._render)
