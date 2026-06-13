"""Matplotlib LCA results plots (subclasses of :class:`~activity_browser.ui.widgets.ABPlot`).

Each class implements ``plot(...)`` and finishes with :meth:`ABPlot.finish_plot`.
Contributor label resolution lives in ``bwutils.contribution_labels``.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from bw2data import methods
from qtpy import QtCore

from activity_browser.ui.widgets import ABPlot
from activity_browser.bwutils.commontasks import unit_of_method
from activity_browser.bwutils.contribution_labels import (
    REST_ROWS,
    contribution_column_labels,
    contribution_row_labels,
)
from activity_browser.bwutils.lcia_overview import LCIAOverviewData, LCIAOverviewPanel


class _ContributionFrame(NamedTuple):
    dfp: pd.DataFrame
    full_rows: list[str]
    full_cols: list[str]
    bar_values: np.ndarray
    col_scores: dict[str, float]
    col_units: dict[str, str]
    relative: bool
    horizontal: bool
    unit: str | None


class LCIAResultsOverviewPlot(ABPlot):
    """Grouped (never stacked) bars for the LCIA landing tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "LCA scores"
        self._overview: LCIAOverviewData | None = None
        self._relative = True
        self._horizontal = False

    @staticmethod
    def _panel_from_data(data: LCIAOverviewData, title: str = "") -> LCIAOverviewPanel:
        return LCIAOverviewPanel(
            title=title,
            values=data.values,
            absolute_values=data.absolute_values,
            group_labels=data.group_labels,
            series_labels=data.series_labels,
            group_units=data.group_units,
            y_label=data.y_label,
        )

    def _configure_figure_layout(self, *, n_panels: int = 1, max_groups: int = 0) -> None:
        self.figure.set_constrained_layout(True)
        nrows, _ = self.near_square_subplot_grid(n_panels) if n_panels > 1 else (1, 1)
        if self._horizontal:
            w_pad, h_pad = 0.22, 0.06
        elif not self._horizontal and max_groups > self.CATEGORY_ROTATE_LABELS_ABOVE:
            w_pad, h_pad = 0.04, 0.18
        else:
            w_pad, h_pad = 0.04, 0.08
        self.figure.set_constrained_layout_pads(
            w_pad=w_pad,
            h_pad=h_pad,
            hspace=0.14 if nrows > 1 else 0.08,
            wspace=0.08,
        )

    def format_bar_tooltip(self, series_idx: int, bar_idx: int, value: float) -> str:
        panel = (self._current_bar_ctx or {}).get("panel")
        if panel is None:
            return super().format_bar_tooltip(series_idx, bar_idx, value)
        group = panel.group_labels[bar_idx]
        series = panel.series_labels[series_idx]
        series_units = getattr(self._overview, "series_units", {}) or {}
        unit = panel.group_units.get(group, "") or series_units.get(series, "")
        absolute_value = (
            float(panel.absolute_values[bar_idx, series_idx]) if self._relative else None
        )
        value_lines = self.tooltip_value_lines(
            value,
            relative=self._relative,
            unit=unit,
            absolute_value=absolute_value,
            relative_already_percent=True,
        )
        header = [series, group] if len(panel.series_labels) > 1 else [group]
        return self.compose_bar_tooltip(header, value_lines)

    def _axis_context(self, ax, panel: LCIAOverviewPanel, group_labels, *, horizontal: bool) -> dict:
        tip_x, tip_y = self.category_axis_tooltips(group_labels, horizontal=horizontal)
        return {
            "ax": ax,
            "panel": panel,
            "bar_values": panel.values.T,
            "full_title": panel.title or None,
            "tooltip_x": tip_x,
            "tooltip_y": tip_y,
        }

    def _draw_panel(
        self,
        ax,
        panel: LCIAOverviewPanel,
        *,
        horizontal: bool,
        show_ylabel: bool = True,
        show_legend: bool = True,
        grid_ncols: int = 1,
        legend_width_ratio: float = 0.0,
    ) -> tuple[int, int]:
        n_groups, n_series = len(panel.group_labels), len(panel.series_labels)
        if n_groups == 0 or n_series == 0:
            return 0, 0

        categories = self.set_category_positions(ax, n_groups, horizontal=horizontal)
        group_width = min(0.9, 0.15 * n_series * n_groups)
        bar_thickness = group_width / max(n_series, 1)
        palette = self.series_colors(n_series)
        legend = self.legend_labels(panel.series_labels)

        for s_idx in range(n_series):
            offsets = categories - group_width / 2 + bar_thickness / 2 + s_idx * bar_thickness
            self.plot_bar_strip(
                ax,
                offsets,
                panel.values[:, s_idx],
                bar_thickness,
                palette[s_idx],
                legend[s_idx],
                horizontal=horizontal,
            )

        self._set_category_ticklabels(
            ax,
            panel.group_labels,
            horizontal=horizontal,
            grid_ncols=grid_ncols,
            legend_width_ratio=legend_width_ratio,
        )
        if show_ylabel and panel.y_label:
            (ax.set_xlabel if horizontal else ax.set_ylabel)(panel.y_label)
        self.set_signed_value_grid(ax, horizontal=horizontal)
        if show_legend and n_series >= 1:
            self.add_legend(loc="upper left", bbox_to_anchor=(1.02, 1), ax=ax)
        return n_groups, n_series

    def plot(
        self,
        data: LCIAOverviewData,
        *,
        relative: bool = True,
        horizontal: bool = False,
    ) -> None:
        self.reset_plot()
        self._overview = data
        self._relative = relative
        self._horizontal = horizontal
        self.reset_minimum_figure_height()

        if data.panels:
            self._plot_panels(data, horizontal=horizontal)
            return

        if not data.group_labels or not data.series_labels:
            self.canvas.draw()
            return

        self._configure_figure_layout(n_panels=1, max_groups=len(data.group_labels))
        panel = self._panel_from_data(data)
        group_labels = panel.group_labels
        self._draw_panel(self.ax, panel, horizontal=horizontal)
        self.set_axis_contexts([self._axis_context(self.ax, panel, group_labels, horizontal=horizontal)])
        self.finish_plot(tooltip_legend=data.series_labels)

    def _plot_panels(self, data: LCIAOverviewData, *, horizontal: bool) -> None:
        panels = data.panels
        n_panels = len(panels)
        nrows, ncols = self.near_square_subplot_grid(n_panels)
        legend_ratio = self.legend_column_width_ratio()

        self.figure.clf()
        gs = GridSpec(
            nrows,
            ncols + 1,
            figure=self.figure,
            width_ratios=[1.0] * ncols + [legend_ratio],
        )

        axis_contexts: list[dict] = []
        first_ax = None
        max_items = 0
        legend_labels: list[str] = []
        for idx, panel in enumerate(panels):
            row, col = divmod(idx, ncols)
            ax = self.figure.add_subplot(gs[row, col])
            first_ax = first_ax or ax
            n_groups, n_series = self._draw_panel(
                ax,
                panel,
                horizontal=horizontal,
                show_legend=False,
                grid_ncols=ncols,
                legend_width_ratio=legend_ratio,
            )
            ax.set_title(self.format_title(panel.title))
            axis_contexts.append(
                self._axis_context(ax, panel, panel.group_labels, horizontal=horizontal)
            )
            if idx == 0:
                legend_labels = panel.series_labels
            max_items = max(max_items, n_groups, n_series)

        for idx in range(n_panels, nrows * ncols):
            row, col = divmod(idx, ncols)
            self.figure.add_subplot(gs[row, col]).set_visible(False)

        if first_ax is not None and legend_labels:
            legend_ax = self.figure.add_subplot(gs[:, ncols])
            legend_ax.axis("off")
            handles, _ = first_ax.get_legend_handles_labels()
            self.add_legend(
                handles,
                self.legend_labels(legend_labels),
                loc="center left",
                borderaxespad=0,
                handlelength=1.2,
                handletextpad=0.5,
                ax=legend_ax,
            )

        self._configure_figure_layout(n_panels=n_panels, max_groups=max_items)
        self.ax = first_ax if first_ax is not None else self.figure.add_subplot(111)
        self.set_axis_contexts(axis_contexts)
        self.reset_minimum_figure_height()
        self.finish_plot(tooltip_legend=legend_labels or None)


class ContributionPlot(ABPlot):
    """Stacked bar chart of process/flow contributions."""

    MAX_LEGEND = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Contributions"
        self.parent = parent

    def format_bar_tooltip(self, container_idx: int, category_idx: int, value: float) -> str:
        # Stacked bars: container = contributor row, patch = category column.
        contributor = self.full_row_labels[container_idx]
        col = self.full_col_labels[category_idx]
        unit = self.col_units.get(col) if self.col_units else self.plot_unit
        share_pct = None
        if not self.plot_relative and (score := self.col_scores.get(col)):
            share_pct = 100.0 * value / score
        value_lines = self.tooltip_value_lines(
            value,
            relative=self.plot_relative,
            unit=unit,
            relative_share_percent=share_pct,
            relative_already_percent=self.plot_relative,
        )
        header = [col, contributor] if len(self.full_col_labels) > 1 and col else [contributor]
        return self.compose_bar_tooltip(header, value_lines)

    def _prepare_data(self, df: pd.DataFrame, unit: str | None) -> _ContributionFrame:
        horizontal = self.use_horizontal_bars()
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
        dfp = dfp.drop(
            dfp.index[(dfp == 0).all(axis=1) & ~dfp.index.isin(REST_ROWS)]
        )
        full_rows = [str(i).strip() for i in dfp.index]
        dfp = dfp[value_cols]
        dfp.columns = full_cols
        return _ContributionFrame(
            dfp, full_rows, full_cols, dfp.to_numpy(dtype=float),
            col_scores, col_units, relative, horizontal, unit,
        )

    @staticmethod
    def _draw_net_markers(ax, dfp: pd.DataFrame, *, horizontal: bool) -> None:
        """Black dot at bar tip when positive and negative stacks do not cancel."""
        kw = dict(
            markersize=5,
            marker="o",
            linestyle="none",
            markerfacecolor="black",
            markeredgecolor="black",
        )
        for i in range(dfp.shape[1]):
            s = dfp.iloc[:, i]
            total, abs_total = float(s.sum()), float(s.abs().sum())
            if math.isclose(abs(total), abs_total, rel_tol=1e-9, abs_tol=1e-15):
                continue
            ax.plot(*(total, i) if horizontal else (i, total), **kw)

    def plot(self, df: pd.DataFrame, unit: str = None):
        frame = self._prepare_data(df, unit)
        self.reset_plot()
        self.reset_minimum_figure_height()

        dfp = frame.dfp.copy()
        display_rows = self.shorten_labels(frame.full_rows)
        dfp.index = pd.Index(display_rows)
        dfp.columns = pd.Index(self.shorten_labels(frame.full_cols))
        row_colors = self.stack_contributor_colors(frame.full_rows, display_rows)
        show_legend = dfp.shape[0] < self.MAX_LEGEND
        legend_ratio = 0.18 if show_legend else 0.0

        plot_kw = dict(stacked=True, color=row_colors, ax=self.ax, legend=False)
        if frame.horizontal:
            dfp.T.plot.barh(**plot_kw)
            self.ax.invert_yaxis()
            if frame.unit:
                self.ax.set_xlabel(frame.unit)
        else:
            dfp.T.plot.bar(**plot_kw)
            if frame.unit:
                self.ax.set_ylabel(frame.unit)

        self._set_category_ticklabels(
            self.ax, frame.full_cols, horizontal=frame.horizontal, legend_width_ratio=legend_ratio
        )
        self.set_signed_value_grid(self.ax, horizontal=frame.horizontal)
        if show_legend:
            handles, _ = self.ax.get_legend_handles_labels()
            if not handles:
                handles = [c.patches[0] for c in self.ax.containers if c.patches]
            self.add_legend(
                handles, self.legend_labels(frame.full_rows),
                loc="center left", bbox_to_anchor=(1, 0.5),
            )

        self._draw_net_markers(self.ax, dfp, horizontal=frame.horizontal)
        self.set_plot_context(
            unit=frame.unit,
            relative=frame.relative,
            row_labels=frame.full_rows,
            col_labels=frame.full_cols,
            bar_values=frame.bar_values,
            col_scores=frame.col_scores,
            col_units=frame.col_units,
        )
        tip_x, tip_y = self.category_axis_tooltips(frame.full_cols, horizontal=frame.horizontal)
        self.finish_plot(
            tooltip_x=tip_x,
            tooltip_y=tip_y,
            tooltip_legend=frame.full_rows if show_legend else None,
        )


class MonteCarloPlot(ABPlot):
    """Overlaid histograms with mean lines per reference flow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Monte Carlo"

    def plot(self, df: pd.DataFrame, method: tuple):
        self.reset_plot()
        self.reset_minimum_figure_height()
        n_series = df.shape[1]
        unit = methods[method]["unit"]
        legend_full = [str(c) for c in df.columns]
        hist_series: list[np.ndarray] = []

        for j in range(n_series):
            vals = np.ravel(np.asarray(df.iloc[:, j].dropna(), dtype=float))
            hist_series.append(vals)
            if vals.size == 0:
                continue
            color = self.series_color(j)
            self.ax.hist(
                vals, density=True, alpha=0.5,
                label=self.legend_labels([legend_full[j]])[0], color=color,
            )
            self.ax.axvline(float(np.mean(vals)), color=color)

        self.ax.set_xlabel(unit)
        self.ax.set_ylabel("Probability")
        if n_series:
            self.add_legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
        self.set_plot_context(unit=unit, col_labels=legend_full, hist_series=hist_series)
        self.finish_plot(tooltip_legend=legend_full if n_series else None)


class GSAPlot(ABPlot):
    """Delta sensitivity indices with confidence intervals."""

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

        if self._plot_df is None:
            return
        self.setMinimumHeight(0)
        self.reset_plot()

        dfp = self._plot_df.dropna(subset=["delta", "delta_conf"]).head(max(1, int(self._max_rows))).copy()
        if dfp.empty:
            self.canvas.draw()
            self._schedule_figure_sync()
            return

        horizontal = self.use_horizontal_bars()
        positions = np.arange(len(dfp))
        deltas = dfp["delta"].to_numpy(dtype=float)
        conf = dfp["delta_conf"].to_numpy(dtype=float)
        colors = [self.gsa_type_color(t) for t in dfp[GSA_TYPE_COLUMN]]
        names = [str(n) for n in dfp[GSA_NAME_COLUMN]]
        handles = [
            Patch(color=self.gsa_type_color(t), label=t)
            for t in dfp[GSA_TYPE_COLUMN].drop_duplicates()
        ]
        err_kw = dict(capsize=3, ecolor="#333333")
        legend_ratio = 0.18 if handles else 0.0
        value_label = "Delta sensitivity index"

        if horizontal:
            self.ax.barh(positions, deltas, xerr=conf, color=colors, height=0.75, **err_kw)
            self.set_category_positions(self.ax, len(dfp), horizontal=True)
            self.ax.set_xlabel(value_label)
            self.ax.tick_params(axis="y", length=0)
            grid_axis = "x"
        else:
            self.ax.bar(positions, deltas, yerr=conf, color=colors, width=0.75, **err_kw)
            self.set_category_positions(self.ax, len(dfp), horizontal=False)
            self.ax.set_ylabel(value_label)
            self.ax.tick_params(axis="x", length=0)
            grid_axis = "y"

        self._set_category_ticklabels(
            self.ax, names, horizontal=horizontal, legend_width_ratio=legend_ratio
        )
        self.ax.grid(which="major", axis=grid_axis, color="grey", linestyle="dashed")
        self.ax.set_axisbelow(True)

        if handles:
            self.figure.set_constrained_layout(True)
            self.figure.set_constrained_layout_pads(w_pad=0.14, h_pad=0.06)
            self.add_legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5))

        self.set_plot_context(
            row_labels=names,
            bar_values=deltas.reshape(1, -1),
            bar_errors=conf.reshape(1, -1),
        )
        tip_x, tip_y = self.category_axis_tooltips(names, horizontal=horizontal)
        self.finish_plot(tooltip_x=tip_x, tooltip_y=tip_y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._plot_df is not None and not self._plot_df.empty:
            QtCore.QTimer.singleShot(0, self._render)
