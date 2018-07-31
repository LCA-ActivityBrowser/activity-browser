# -*- coding: utf-8 -*-
import math

import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtWidgets

from ..bwutils.commontasks import format_activity_label, wrap_text
from brightway2 import get_activity

class Plot(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Plot, self).__init__(parent)
        # create figure, canvas, and axis
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)  # create an axis

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def get_canvas_size_in_inches(self):
        print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def savefilepath(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            'Choose location to save lca results'
        )
        return filepath

    def to_png(self):
        """ Export to .png format. """
        filepath = self.savefilepath()
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath()
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            self.figure.savefig(filepath)

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
        print("Canvas size:", canvas_size)
        size = (4 + len(labels) * 0.3, 4 + len(labels) * 0.3)
        self.figure.set_size_inches(size[0], size[1])

        df = pd.DataFrame(data=mlca.results_normalized.T, columns=labels)
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

class LCAResultsBarChart(Plot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    def __init__(self, parent=None, *args):
        super(LCAResultsBarChart, self).__init__(parent, *args)

    def plot(self, mlca, method=None):

        self.ax.clear()

        if method == None:
            method = mlca.methods[0]

        functional_units = [str(get_activity(list(func_unit.keys())[0])) for func_unit in mlca.func_units]
        values = mlca.results[:, mlca.methods.index(method)]
        y_pos = np.arange(len(functional_units))

        color_iterate = iter(plt.rcParams['axes.prop_cycle'])
        for i in range(len(values)):
            self.ax.barh(y_pos[i], values[i], align='center', color=next(color_iterate)['color'], alpha=0.8)
        self.ax.set_yticks(y_pos)
        self.ax.set_xlabel('Score')
        self.ax.set_title('LCA scores compared')
        self.ax.set_yticklabels(functional_units, minor= False)


        self.canvas.figure
        self.canvas.draw()


class LCAResultsPlot(Plot):
    def __init__(self, parent=None, *args):
        super(LCAResultsPlot, self).__init__(parent, *args)

    def plot(self, mlca, normalised=False):
        """ Plot a heatmap grid of the different methods and functional units. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

        activity_names = [
            format_activity_label(next(iter(f.keys())), style='pnl') for f in mlca.func_units
        ]

        # From https://stanford.edu/~mwaskom/software/seaborn/tutorial/color_palettes.html
        # cmap = sns.cubehelix_palette(8, start=.5, rot=-.75, as_cmap=True)

        if normalised:
            self.use_results = mlca.results_normalized  # Normalize to get relative results
        else:
            self.use_results = mlca.results

        hm = sns.heatmap(
            self.use_results,
            annot=True,
            linewidths=.05,
            # cmap=cmap,
            xticklabels=[wrap_text(",".join(x), max_length=40) for x in mlca.methods],
            yticklabels=activity_names,
            ax=self.ax,
            # cbar_ax=self.axcb,
            square=False,
            annot_kws={"size": 11 if len(mlca.methods) <= 8 else 9,
                       'rotation': 0 if len(mlca.methods) <= 8 else 60}
        )
        hm.tick_params(labelsize=8)

        # refresh canvas
        size_inches = (2 + len(mlca.methods) * 0.5, 4 + len(activity_names) * 0.55)
        # self.figure.set_size_inches(size[0], size[1])
        self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class ProcessContributionPlot(Plot):
    def __init__(self, parent=None, *args):
        super(ProcessContributionPlot, self).__init__(parent, *args)
        self.df_tc = pd.DataFrame()

    def plot(self, mlca, method=None, func=None, limit=5, limit_type="number", per="method", normalised=True):
        """ Plot a horizontal bar chart of the process contributions. """
        self.ax.clear()
        height = 4 + len(mlca.func_units) * 1
        self.figure.set_figheight(height)

        if per == "method":
            tc = mlca.top_process_contributions_per_method(method_name=method, limit=limit, normalised=normalised,
                                                           limit_type=limit_type)
        elif per == "func":
            tc = mlca.top_process_contributions_per_func(func_name=func, limit=limit, normalised=normalised,
                                                           limit_type=limit_type)
        else:
            print("Unknown type requested")
            return None
        self.df_tc = pd.DataFrame(tc)
        self.df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        self.df_tc.index = [format_activity_label(a, style='pnl', max_length=30) for a in self.df_tc.index]
        if not normalised:
            self.df_tc_plot = self.df_tc.drop("Total")
        else:
            self.df_tc_plot = self.df_tc
        plot = self.df_tc_plot.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plt.rc('legend', **{'fontsize': 8})  # putting below affects only LCAElementaryFlowContributionPlot
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                    ncol=math.ceil((len(self.df_tc.index) * 0.22) / height))
        plot.grid(b=False)

        # refresh canvas
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class InventoryCharacterisationPlot(Plot):
    def __init__(self, parent=None, *args):
        super(InventoryCharacterisationPlot, self).__init__(parent, *args)

    def plot(self, mlca, method=None, func=None, limit=5, limit_type="number", per="method", normalised=True):
        """ Plot a horizontal bar chart of the inventory characterisation. """
        self.ax.clear()
        height = 3 + len(mlca.func_units) * 0.5
        self.figure.set_figheight(height)

        if per == "method":
            tc = mlca.top_elementary_flow_contributions_per_method(method_name=method, limit=limit, normalised=normalised,
                                                           limit_type=limit_type)
        elif per == "func":
            tc = mlca.top_elementary_flow_contributions_per_func(func_name=func, limit=limit, normalised=normalised,
                                                           limit_type=limit_type)
        else:
            print("Unknown type requested")
            return None


        self.df_tc = pd.DataFrame(tc)
        self.df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        self.df_tc.index = [format_activity_label(a, style='bio') for a in self.df_tc.index]
        if not normalised:
            self.df_tc_plot = self.df_tc.drop("Total")
        else:
            self.df_tc_plot = self.df_tc
        plot = self.df_tc_plot.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.rc('legend', **{'fontsize': 8})
        plot.grid(b=False)

        # refresh canvas
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])