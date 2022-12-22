# -*- coding: utf-8 -*-
import math

import brightway2 as bw
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from PySide2 import QtWidgets
import seaborn as sns

from activity_browser.utils import savefilepath
from ..bwutils.commontasks import wrap_text


# todo: sizing of the figures needs to be improved and systematized...
# todo: Bokeh is a potential alternative as it allows interactive visualizations,
#  but this issue needs to be resolved first: https://github.com/bokeh/bokeh/issues/8169

class Plot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)
        # create figure, canvas, and axis
        # self.figure = Figure(tight_layout=True)
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)  # create an axis
        self.plot_name = 'Figure'

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def reset_plot(self) -> None:
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

    def get_canvas_size_in_inches(self):
        # print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def to_png(self):
        """ Export to .png format. """
        filepath = savefilepath(default_file_name=self.plot_name, file_filter=self.PNG_FILTER)
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = savefilepath(default_file_name=self.plot_name, file_filter=self.SVG_FILTER)
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            self.figure.savefig(filepath)


class LCAResultsBarChart(Plot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA scores'

    def plot(self, df: pd.DataFrame, method: tuple, labels: list):
        self.reset_plot()
        height_inches, width_inches = self.get_canvas_size_in_inches()
        self.figure.set_size_inches(height_inches, width_inches)

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/489
        df.index = pd.Index(labels)  # Replace index of tuples
        show_legend = df.shape[1] != 1  # Do not show the legend for 1 column
        df.plot.barh(ax=self.ax, legend=show_legend)
        self.ax.invert_yaxis()

        # labels
        self.ax.set_yticks(np.arange(len(labels)))
        self.ax.set_xlabel(bw.methods[method].get('unit'))
        self.ax.set_title(', '.join([m for m in method]))
        # self.ax.set_yticklabels(labels, minor=False)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # draw
        self.canvas.draw()


class LCAResultsPlot(Plot):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA heatmap'

    def plot(self, df: pd.DataFrame):
        """ Plot a heatmap grid of the different impact categories and reference flows. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()

        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if "amount" in dfp.columns:
            dfp.drop(["amount"], axis=1, inplace=True)  # Drop the 'amount' col
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=20) for i in dfp.columns]

        sns.heatmap(
            dfp, ax=self.ax, cmap="Blues", annot=True, linewidths=0.05,
            annot_kws={"size": 11 if dfp.shape[1] <= 8 else 9,
                       "rotation": 0 if dfp.shape[1] <= 8 else 60}
        )
        self.ax.tick_params(labelsize=8)
        if dfp.shape[1] > 5:
            self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation="vertical")
        self.ax.set_yticklabels(self.ax.get_yticklabels(), rotation="horizontal")

        # refresh canvas
        size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[0] * 0.55)
        self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])

        self.canvas.draw()


class ContributionPlot(Plot):
    MAX_LEGEND = 30

    def __init__(self):
        super().__init__()
        self.plot_name = 'Contributions'

    def plot(self, df: pd.DataFrame, unit: str = None):
        """ Plot a horizontal bar chart of the process contributions. """
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        self.ax.clear()
        canvas_width_inches, canvas_height_inches = self.get_canvas_size_in_inches()
        optimal_height_inches = 4 + dfp.shape[1] * 0.55
        # print('Optimal Contribution plot height:', optimal_height_inches)
        self.figure.set_size_inches(canvas_width_inches, optimal_height_inches)

        # avoid figures getting too large horizontally
        dfp.index = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.index])
        dfp.columns = pd.Index([wrap_text(i, max_length=40) for i in dfp.columns])
        # Strip invalid characters from the ends of row/column headers
        dfp.index = dfp.index.str.strip("_ \n\t")
        dfp.columns = dfp.columns.str.strip("_ \n\t")

        dfp.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax,
            legend=False if dfp.shape[0] >= self.MAX_LEGEND else True,
        )
        self.ax.tick_params(labelsize=8)
        if unit:
            self.ax.set_xlabel(unit)

        # show legend if not too many items
        if not dfp.shape[0] >= self.MAX_LEGEND:
            plt.rc('legend', **{'fontsize': 8})
            ncols = math.ceil(dfp.shape[0] * 0.6 / optimal_height_inches)
            # print('Ncols:', ncols, dfp.shape[0] * 0.55, optimal_height_inches)
            self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=ncols)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # refresh canvas
        # size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[1] * 0.55)
        # self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])

        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])
        self.canvas.draw()


class CorrelationPlot(Plot):
    def __init__(self, parent=None):
        super().__init__(parent)
        sns.set(style="darkgrid")

    def plot(self, df: pd.DataFrame):
        """ Plot a heatmap of correlations between different reference flows. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()
        canvas_size = self.canvas.get_width_height()
        # print("Canvas size:", canvas_size)
        size = (4 + df.shape[1] * 0.3, 4 + df.shape[1] * 0.3)
        self.figure.set_size_inches(size[0], size[1])

        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
        sns.heatmap(corr, mask=mask, cmap=plt.cm.PuOr, vmin=-vmax, vmax=vmax,
                    square=True, linecolor="lightgray", linewidths=1, ax=self.ax)

        df_lte8_cols = df.shape[1] <= 8
        for i in range(len(corr)):
            self.ax.text(
                i + 0.5, i + 0.5, corr.columns[i], ha="center", va="center",
                rotation=0 if df_lte8_cols else 45, size=11 if df_lte8_cols else 9
            )
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                self.ax.text(
                    j + 0.5, i + 0.5, s, ha="center", va="center",
                    rotation=0 if df_lte8_cols else 45, size=11 if df_lte8_cols else 9
                )
        self.ax.axis("off")

        # refresh canvas
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])
        self.canvas.draw()


class MonteCarloPlot(Plot):
    """ Monte Carlo plot."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'Monte Carlo'

    def plot(self, df: pd.DataFrame, method: tuple):
        self.ax.clear()

        for col in df.columns:
            color = self.ax._get_lines.get_next_color()
            df[col].hist(ax=self.ax, figure=self.figure, label=col, density=True, color=color, alpha=0.5)  # , histtype="step")
            # self.ax.axvline(df[col].median(), color=color)
            self.ax.axvline(df[col].mean(), color=color)

        self.ax.set_xlabel(bw.methods[method]["unit"])
        self.ax.set_ylabel('Probability')
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), ) #ncol=2

        # lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]

        self.canvas.draw()


class SimpleDistributionPlot(Plot):
    def plot(self, data: np.ndarray, mean: float, label: str = "Value"):
        self.reset_plot()
        try:
            sns.histplot(data.T, kde=True, stat="density", ax=self.ax, edgecolor="none")
        except RuntimeError as e:
            print("Runtime error: {}\nPlotting without KDE.".format(e))
            sns.histplot(data.T, kde=False, stat="density", ax=self.ax, edgecolor="none")
        self.ax.set_xlabel(label)
        self.ax.set_ylabel("Probability density")
        # Add vertical line at given mean of x-axis
        self.ax.axvline(mean, label="Mean / amount", c="r", ymax=0.98)
        self.ax.legend(loc="upper right")
        _, height = self.canvas.get_width_height()
        self.setMinimumHeight(height / 2)
        self.canvas.draw()
