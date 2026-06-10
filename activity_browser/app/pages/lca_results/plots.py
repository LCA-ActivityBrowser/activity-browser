import math
from loguru import logger

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import seaborn as sns

from bw2data import methods
from qtpy import QtCore
from activity_browser.ui.widgets import ABPlot
from activity_browser.bwutils.commontasks import wrap_text





class LCAResultsBarChart(ABPlot):
    """ " Generate a bar chart comparing the absolute LCA scores of the products"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "LCA scores"

    def plot(self, df: pd.DataFrame, method: tuple, labels: list):
        self.reset_plot()
        width_inches, height_inches = self.get_canvas_size_in_inches()
        self.figure.set_size_inches(width_inches, height_inches, forward=False)

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/489
        df.index = pd.Index(labels)  # Replace index of tuples
        show_legend = df.shape[1] != 1  # Do not show the legend for 1 column
        df.plot.barh(ax=self.ax, legend=show_legend)
        self.ax.invert_yaxis()

        # labels
        self.ax.set_yticks(np.arange(len(labels)))
        self.ax.set_xlabel(methods[method].get("unit"))
        self.ax.set_title(", ".join([m for m in method]))
        # self.ax.set_yticklabels(labels, minor=False)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        self._set_plot_chrome_white()
        # draw
        self.canvas.draw()
        self._schedule_figure_sync()


class LCAResultsPlot(ABPlot):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "LCA heatmap"

    def plot(self, df: pd.DataFrame, invert_plot: bool = False):
        """Plot a heatmap grid of the different impact categories and reference flows."""
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()

        dfp = df.copy()
        dfp.index = dfp["index"]
        dfp.drop(
            dfp.select_dtypes(["object"]), axis=1, inplace=True
        )  # get rid of all non-numeric columns (metadata)
        if "amount" in dfp.columns:
            dfp.drop(["amount"], axis=1, inplace=True)  # Drop the 'amount' col
        if "Score" in dfp.index:
            dfp.drop("Score", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=20) for i in dfp.columns]
        prop = dfp.divide(dfp.abs().max(axis=0)).multiply(100)
        dfp.replace(np.nan, 0, inplace=True)
        if invert_plot:
            dfp = dfp.T
            prop = prop.T

        # set different color palette depending on whether all values are positive or not
        if (
            dfp.min(axis=None) < 0 and dfp.max(axis=None) > 0
        ):  # has both negative AND positive values
            cmap = sns.color_palette("vlag_r", as_cmap=True)
        else:  # has only positive OR negative values
            cmap = sns.color_palette("Blues", as_cmap=True)

        sns.heatmap(
            prop,
            ax=self.ax,
            cmap=cmap,
            annot=dfp,
            linewidths=0.05,
            annot_kws={
                "size": 11 if dfp.shape[1] <= 8 else 9,
                "rotation": 0 if dfp.shape[1] <= 8 else 60,
            },
            cbar=False,
        )
        self.ax.tick_params(labelsize=8)
        if dfp.shape[1] > 5:
            self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation="vertical")
        self.ax.set_yticklabels(self.ax.get_yticklabels(), rotation="horizontal")

        # refresh canvas — width from Qt layout, height from data (vertical scroll)
        height_inches = 4 + dfp.shape[0] * 0.55
        self.figure.set_size_inches(
            self.get_canvas_size_in_inches()[0], height_inches, forward=False
        )
        self.set_minimum_height_for_figure_inches(height_inches)

        self._set_plot_chrome_white()
        self.canvas.draw()
        self._schedule_figure_sync()


class ContributionPlot(ABPlot):
    MAX_LEGEND = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Contributions"
        self.parent = parent

    def plot(self, df: pd.DataFrame, unit: str = None):
        """Plot a horizontal stacked bar chart of contributions,
        add 'total' marker if both positive and negative results are present."""
        dfp = df.copy()
        dfp = dfp.iloc[:, ::-1]  # reverse column names so they align with calculation setup and rest of results

        dfp.index = dfp["index"]
        dfp.drop(
            dfp.select_dtypes(["object"]), axis=1, inplace=True
        )  # get rid of all non-numeric columns (metadata)
        if "Score" in dfp.index:
            dfp.drop("Score", inplace=True)
        if "id" in dfp:
            dfp.drop(columns=["id"], inplace=True)
        # drop rows if all values are 0 except for "Rest (+)" and "Rest (-)"
        rows_to_drop = dfp.index[(dfp == 0).all(axis=1) & ~dfp.index.isin(["Rest (+)", "Rest (-)"])]
        # Drop those rows
        dfp = dfp.drop(rows_to_drop)

        self.ax.clear()
        canvas_width_inches, canvas_height_inches = self.get_canvas_size_in_inches()
        optimal_height_inches = 4 + dfp.shape[1] * 0.55
        # print('Optimal Contribution plot height:', optimal_height_inches)
        self.figure.set_size_inches(
            canvas_width_inches, optimal_height_inches, forward=False
        )

        # avoid figures getting too large horizontally
        dfp.index = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.index])
        dfp.columns = pd.Index([wrap_text(i, max_length=40) for i in dfp.columns])
        # Strip invalid characters from the ends of row/column headers
        dfp.index = dfp.index.str.strip("_ \n\t")
        dfp.columns = dfp.columns.str.strip("_ \n\t")

        # set colormap to use
        items = dfp.shape[0]  # how many contribution items
        # skip grey and black at start/end of cmap
        cmap = plt.cm.nipy_spectral_r(np.linspace(0, 1, items + 2))[1:-1]
        colors = {item: color for item, color in zip(dfp.index, cmap)}
        # overwrite rest values to grey
        colors["Rest (+)"] = [0.8, 0.8, 0.8, 1.]
        colors["Rest (-)"] = [0.8, 0.8, 0.8, 1.]

        dfp.T.plot.barh(
            stacked=True,
            color=colors,
            ax=self.ax,
            legend=False if dfp.shape[0] >= self.MAX_LEGEND else True,
        )
        self.ax.tick_params(labelsize=8)
        if unit:
            self.ax.set_xlabel(unit)

        # show legend if not too many items
        if not dfp.shape[0] >= self.MAX_LEGEND:
            plt.rc("legend", **{"fontsize": 8})
            ncols = math.ceil(dfp.shape[0] * 0.6 / optimal_height_inches)
            # print('Ncols:', ncols, dfp.shape[0] * 0.55, optimal_height_inches)
            self.ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), ncol=ncols)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
        self.ax.set_axisbelow(True)  # puts gridlines behind bars
        # make the zero line more present
        grid = self.ax.get_xgridlines()
        # get the 0 line from all gridlines
        label_pos = [i for i, label in enumerate(self.ax.get_xticklabels()) if label.get_position()[0] == 0.0]
        if len(label_pos) > 0:
            zero_line = grid[label_pos[0]]
            zero_line.set_color("black")
            zero_line.set_linestyle("solid")

        # total marker when enabled and both negative and positive results are present in a column
        if self.parent.score_marker:
            marker_size = max(min(150 / dfp.shape[1], 35), 10)  # set marker size dynamic between 10 - 35
            # Use iloc so each column is always a 1D Series (duplicate column labels make dfp[col] a DataFrame).
            for i in range(dfp.shape[1]):
                s = dfp.iloc[:, i]
                total = float(s.sum())
                abs_total = float(s.abs().sum())
                if not math.isclose(abs(total), abs_total, rel_tol=1e-9, abs_tol=1e-15):
                    self.ax.plot(total, i,
                                 markersize=marker_size, marker="d", fillstyle="left",
                                 markerfacecolor="black", markerfacecoloralt="grey", markeredgecolor="white")

        # TODO review: remove or enable

        # refresh canvas
        # size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[1] * 0.55)
        # self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])

        self.set_minimum_height_for_figure_inches(optimal_height_inches)
        self._set_plot_chrome_white()
        self.canvas.draw()
        self._schedule_figure_sync()


class CorrelationPlot(ABPlot):
    def __init__(self, parent=None):
        super().__init__(parent)
        sns.set(style="darkgrid")

    def plot(self, df: pd.DataFrame):
        """Plot a heatmap of correlations between different reference flows."""
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()
        canvas_width_inches, _ = self.get_canvas_size_in_inches()
        height_inches = 4 + df.shape[1] * 0.3
        self.figure.set_size_inches(canvas_width_inches, height_inches, forward=False)

        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
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

        df_lte8_cols = df.shape[1] <= 8
        for i in range(len(corr)):
            self.ax.text(
                i + 0.5,
                i + 0.5,
                corr.columns[i],
                ha="center",
                va="center",
                rotation=0 if df_lte8_cols else 45,
                size=11 if df_lte8_cols else 9,
            )
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                self.ax.text(
                    j + 0.5,
                    i + 0.5,
                    s,
                    ha="center",
                    va="center",
                    rotation=0 if df_lte8_cols else 45,
                    size=11 if df_lte8_cols else 9,
                )
        self.ax.axis("off")

        self.set_minimum_height_for_figure_inches(height_inches)
        self._set_plot_chrome_white()
        self.canvas.draw()
        self._schedule_figure_sync()


class MonteCarloPlot(ABPlot):
    """Monte Carlo plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "Monte Carlo"

    def plot(self, df: pd.DataFrame, method: tuple):
        self.ax.clear()

        # Use Axes.hist per series. Use iloc so duplicate column labels (possible after
        # get_labels) never return a 2-column DataFrame — 2D input makes hist() treat each
        # column as a separate dataset and reject a single color=.
        for j in range(df.shape[1]):
            series = df.iloc[:, j]
            vals = np.ravel(np.asarray(series.dropna(), dtype=float))
            if vals.size == 0:
                continue
            color = self.ax._get_lines.get_next_color()
            label = str(df.columns[j])
            self.ax.hist(
                vals,
                density=True,
                alpha=0.5,
                label=label,
                color=color,
            )
            self.ax.axvline(float(np.mean(vals)), color=color)

        self.ax.set_xlabel(methods[method]["unit"])
        self.ax.set_ylabel("Probability")
        self.ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.07),
        )  # ncol=2

        # lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]

        self._set_plot_chrome_white()
        self.canvas.draw()
        self._schedule_figure_sync()


GSA_TYPE_COLORS = {
    "technosphere": "#1f77b4",
    "biosphere": "#2ca02c",
    "characterization factor": "#ff7f0e",
    "parameter": "#9467bd",
}


class GSAPlot(ABPlot):
    """Horizontal bar chart of SALib delta indices with ``delta_conf`` error bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = "GSA"
        self._plot_df: pd.DataFrame | None = None
        self._max_rows = 10

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

        # Highest delta at the top of a horizontal bar chart.
        dfp = dfp.iloc[::-1]
        n = len(dfp)
        y_pos = np.arange(n)
        deltas = dfp["delta"].to_numpy(dtype=float)
        conf = dfp["delta_conf"].to_numpy(dtype=float)
        colors = [GSA_TYPE_COLORS.get(t, "#7f7f7f") for t in dfp[GSA_TYPE_COLUMN]]
        labels = [wrap_text(str(name), max_length=40) for name in dfp[GSA_NAME_COLUMN]]

        label_fontsize = max(5, min(9, int(height_inches * 72 / max(n, 1) * 0.35)))

        self.ax.barh(y_pos, deltas, xerr=conf, color=colors, capsize=3, ecolor="#333333", height=0.75)
        self.ax.set_yticks(y_pos)
        self.ax.set_yticklabels(labels, fontsize=label_fontsize)
        self.ax.set_xlabel("Delta sensitivity index")
        self.ax.grid(which="major", axis="x", color="grey", linestyle="dashed")
        self.ax.set_axisbelow(True)
        self.ax.tick_params(axis="y", length=0)

        handles = []
        for gsa_type in dfp[GSA_TYPE_COLUMN].drop_duplicates():
            handles.append(
                Patch(
                    color=GSA_TYPE_COLORS.get(gsa_type, "#7f7f7f"),
                    label=gsa_type,
                )
            )
        if handles:
            self.ax.legend(handles=handles, loc="lower right", fontsize=max(6, label_fontsize))

        self._set_plot_chrome_white()
        self.canvas.draw()
        self._schedule_figure_sync()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._plot_df is not None and not self._plot_df.empty:
            QtCore.QTimer.singleShot(0, self._render)
