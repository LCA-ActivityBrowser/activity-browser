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

class CorrelationPlot(Plot):
    def __init__(self, parent=None, *args):
        super(CorrelationPlot, self).__init__(parent, *args)
        sns.set(style="darkgrid")

    def plot(self, mlca, labels):
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


class LCAResultsPlot(Plot):
    def __init__(self, parent=None, *args):
        super(LCAResultsPlot, self).__init__(parent, *args)

    def plot(self, mlca):
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

        activity_names = [
            format_activity_label(next(iter(f.keys())), style='pnl') for f in mlca.func_units
        ]


        # From https://stanford.edu/~mwaskom/software/seaborn/tutorial/color_palettes.html
        # cmap = sns.cubehelix_palette(8, start=.5, rot=-.75, as_cmap=True)
        hm = sns.heatmap(
            # mlca.results_normalized  # Normalize to get relative results
            mlca.results,
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

    def plot(self, mlca, method=None):
        self.ax.clear()
        height = 4 + len(mlca.func_units) * 1
        self.figure.set_figheight(height)

        tc = mlca.top_process_contributions(method_name=method, limit=5, relative=True)
        df_tc = pd.DataFrame(tc)
        df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        df_tc.index = [format_activity_label(a, style='pnl', max_length=30) for a in df_tc.index]
        plot = df_tc.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plt.rc('legend', **{'fontsize': 8})  # putting below affects only LCAElementaryFlowContributionPlot
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                    ncol=math.ceil((len(df_tc.index) * 0.22) / height))
        plot.grid(b=False)

        # refresh canvas
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class ElementaryFlowContributionPlot(Plot):
    def __init__(self, parent=None, *args):
        super(ElementaryFlowContributionPlot, self).__init__(parent, *args)

    def plot(self, mlca, method=None):
        self.ax.clear()
        height = 3 + len(mlca.func_units) * 0.5
        self.figure.set_figheight(height)

        tc = mlca.top_elementary_flow_contributions(method_name=method, limit=5, relative=True)
        df_tc = pd.DataFrame(tc)
        df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        df_tc.index = [format_activity_label(a, style='bio') for a in df_tc.index]
        plot = df_tc.T.plot.barh(
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