# -*- coding: utf-8 -*-
import math
import os

import brightway2 as bw
from bw2data.filesystem import safe_filename
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from PySide2 import QtWidgets
import seaborn as sns

from ..bwutils.commontasks import format_activity_label, wrap_text
from ..settings import ab_settings


# todo: sizing of the figures needs to be improved and systematized...
# todo: Bokeh is a potential alternative as it allows interactive visualizations,
#  but this issue needs to be resolved first: https://github.com/bokeh/bokeh/issues/8169

class Plot(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Plot, self).__init__(parent)
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
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

    def get_canvas_size_in_inches(self):
        # print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def savefilepath(self, default_file_name="LCA results", filter="All Files (*.*)"):
        safe_name = safe_filename(default_file_name, add_hash=False)
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Choose location to save lca results',
            dir=os.path.join(ab_settings.data_dir, safe_name),
            filter=filter,
        )
        return filepath

    def to_png(self):
        """ Export to .png format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, filter="PNG (*.png)")
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, filter="SVG (*.svg)")
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            self.figure.savefig(filepath)


class LCAResultsBarChart(Plot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    def __init__(self, parent=None, *args):
        super(LCAResultsBarChart, self).__init__(parent, *args)
        self.plot_name = 'LCA scores'

    def plot(self, mlca, method=None):
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        height_inches, width_inches = self.get_canvas_size_in_inches()
        self.figure.set_size_inches(height_inches, width_inches)

        if method == None:
            method = mlca.methods[0]

        functional_units = [format_activity_label(next(iter(fu.keys())), style='pnl') for fu in mlca.func_units]

        values = mlca.lca_scores[:, mlca.method_index[method]]
        y_pos = np.arange(len(functional_units))

        # color_iterate = iter(plt.rcParams['axes.prop_cycle'])
        for i in range(len(values)):
            self.ax.barh(y_pos[i], values[i], align='center', alpha=1)  # color=next(color_iterate)['color'],

        # labels
        self.ax.set_yticks(y_pos)
        self.ax.set_xlabel(bw.methods[method].get('unit'))
        self.ax.set_title(', '.join([m for m in method]))
        self.ax.set_yticklabels(functional_units, minor=False)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # draw
        self.canvas.draw()


class LCAResultsPlot(Plot):
    def __init__(self, parent=None, *args):
        super(LCAResultsPlot, self).__init__(parent, *args)
        self.plot_name = 'LCA heatmap'

    def plot(self, df):
        """ Plot a heatmap grid of the different methods and functional units. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=20) for i in dfp.columns]

        hm = sns.heatmap(dfp,
                    ax=self.ax,
                    cmap='Blues',
                    annot=True,
                    linewidths=.05,
                    annot_kws={"size": 11 if dfp.shape[1] <= 8 else 9,
                            'rotation': 0 if dfp.shape[1] <= 8 else 60}
                    )
        hm.tick_params(labelsize=8)
        if dfp.shape[1] > 5:
            self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation='vertical')
        self.ax.set_yticklabels(self.ax.get_yticklabels(), rotation='horizontal')

        # refresh canvas
        size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[0] * 0.55)
        self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])

        self.canvas.draw()


class ContributionPlot(Plot):
    def __init__(self):
        super(ContributionPlot, self).__init__()
        self.plot_name = 'Contributions'

    def plot(self, df, unit=None):
        """ Plot a horizontal bar chart of the process contributions. """
        max_legend_items = 30
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        self.ax.clear()
        canvas_width_inches, canvas_height_inches = self.get_canvas_size_in_inches()
        optimal_height_inches = 4 + dfp.shape[1] * 0.55
        print('Optimal Contribution plot height:', optimal_height_inches)
        self.figure.set_size_inches(canvas_width_inches, optimal_height_inches)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(str(i), max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=40) for i in dfp.columns]

        plot = dfp.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax,
            legend=False if dfp.shape[0] >= max_legend_items else True,
        )
        plot.tick_params(labelsize=8)
        if unit:
            self.ax.set_xlabel(unit)

        # show legend if not too many items
        if not dfp.shape[0] >= max_legend_items:
            plt.rc('legend', **{'fontsize': 8})
            ncols = math.ceil(dfp.shape[0] * 0.6 / optimal_height_inches)
            # print('Ncols:', ncols, dfp.shape[0] * 0.55, optimal_height_inches)
            legend = plot.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=ncols)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # refresh canvas
        # size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[1] * 0.55)
        # self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])

        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])
        self.canvas.draw()

        # self.canvas.draw()
        # size_pixels = self.figure.get_size_inches() * self.figure.dpi
        # self.setMinimumHeight(size_pixels[1])


class CorrelationPlot(Plot):
    def __init__(self, parent=None, *args):
        super(CorrelationPlot, self).__init__(parent, *args)
        sns.set(style="darkgrid")

    def plot(self, mlca, labels):
        """ Plot a heatmap of correlations between different functional units. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        canvas_size = self.canvas.get_width_height()
        # print("Canvas size:", canvas_size)
        size = (4 + len(labels) * 0.3, 4 + len(labels) * 0.3)
        self.figure.set_size_inches(size[0], size[1])

        df = pd.DataFrame(data=mlca.lca_scores_normalized.T, columns=labels)
        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
        sns.heatmap(corr, mask=mask, cmap=plt.cm.PuOr, vmin=-vmax, vmax=vmax,
                    square=True, linecolor="lightgray", linewidths=1, ax=self.ax)
        for i in range(len(corr)):
            self.ax.text(i + 0.5, i + 0.5, corr.columns[i],
                      ha="center", va="center",
                      rotation=0 if len(labels) <= 8 else 45,
                      size=11 if len(labels) <= 8 else 9)
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                self.ax.text(j + 0.5, i + 0.5, s,
                          ha="center", va="center",
                          rotation=0 if len(labels) <= 8 else 45,
                          size=11 if len(labels) <= 8 else 9)
        self.ax.axis("off")

        # refresh canvas
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class MonteCarloPlot(Plot):
    """ Monte Carlo plot."""
    def __init__(self, parent=None):
        super(MonteCarloPlot, self).__init__(parent)
        self.plot_name = 'Monte Carlo'

    def plot(self, df, method):
        # self.figure.clf()
        # self.ax = self.figure.add_subplot(111)
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