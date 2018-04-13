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


class CorrelationPlot(FigureCanvasQTAgg):
    def __init__(self, parent, data, labels, dpi=100):
        figure = Figure(figsize=(4+len(labels)*0.3, 4+len(labels)*0.3), dpi=dpi, tight_layout=True)
        axes = figure.add_subplot(111)

        super(CorrelationPlot, self).__init__(figure)
        self.setParent(parent)

        sns.set(style="darkgrid")

        corr = data
        # cmap = sns.diverging_palette(220, 10, as_cmap=True)
        # corrplot(data, names=labels, annot=True, sig_stars=False,
        #      diag_names=True, cmap=cmap, ax=axes, cbar=True)

        df = pd.DataFrame(data=data, columns=labels)
        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
        sns.heatmap(corr, mask=mask, cmap=plt.cm.PuOr, vmin=-vmax, vmax=vmax,
                    square=True, linecolor="lightgray", linewidths=1, ax=axes)
        for i in range(len(corr)):
            axes.text(i + 0.5, i + 0.5, corr.columns[i],
                      ha="center", va="center",
                      rotation=0 if len(labels) <= 8 else 45,
                      size=11 if len(labels) <= 8 else 9)
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                axes.text(j + 0.5, i + 0.5, s,
                          ha="center", va="center",
                          rotation=0 if len(labels) <= 8 else 45,
                          size=11 if len(labels) <= 8 else 9)
        axes.axis("off")
        # If uncommented, fills widget
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()
        self.setMinimumSize(self.size())


class LCAResultsPlot(FigureCanvasQTAgg):
    def __init__(self, parent, mlca, width=6, height=6, dpi=100):
        activity_names = [
            format_activity_label(next(iter(f.keys())), style='pnl') for f in mlca.func_units
        ]
        figure = Figure(figsize=(2+len(mlca.methods)*0.5, 4+len(activity_names)*0.55),
                        dpi=dpi, tight_layout=True)
        axes = figure.add_subplot(111)

        super(LCAResultsPlot, self).__init__(figure)
        self.setParent(parent)
        # From https://stanford.edu/~mwaskom/software/seaborn/tutorial/color_palettes.html
        cmap = sns.cubehelix_palette(8, start=.5, rot=-.75, as_cmap=True)
        hm = sns.heatmap(
            # mlca.results / np.average(mlca.results, axis=0), # Normalize to get relative results
            mlca.results,
            annot=True,
            linewidths=.05,
            cmap=cmap,
            xticklabels=[wrap_text(",".join(x), max_lenght=40) for x in mlca.methods],
            yticklabels=activity_names,
            ax=axes,
            square=False,
            annot_kws={"size": 11 if len(mlca.methods) <= 8 else 9,
                       'rotation': 0 if len(mlca.methods) <= 8 else 60}
        )
        hm.tick_params(labelsize=8)

        self.setMinimumSize(self.size())
        # sns.set_context("notebook")


class ContributionPlot(QtWidgets.QWidget):
    def __init__(self, parent=None, height=5, width=6, dpi=100):
        super(ContributionPlot, self).__init__(parent)
        # create figure, canvas, and axis
        self.width, self.height = width, height
        self.figure = Figure(figsize=(width, height), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)  # create an axis

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)


class ProcessContributionPlot(ContributionPlot):
    def __init__(self, parent=None, *args):
        super(ProcessContributionPlot, self).__init__(parent, *args)

    def plot(self, mlca, method=None):
        self.ax.clear()
        self.height = 4 + len(mlca.func_units) * 0.3
        self.figure.set_figheight(self.height)

        tc = mlca.top_process_contributions(method_name=method, limit=5, relative=True)
        df_tc = pd.DataFrame(tc)
        df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        df_tc.index = [format_activity_label(a, style='pl') for a in df_tc.index]
        plot = df_tc.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plt.rc('legend', **{'fontsize': 8})  # putting below affects only LCAElementaryFlowContributionPlot
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                    ncol=math.ceil((len(df_tc.index) * 0.22) / self.height))
        plot.grid(b=False)

        # refresh canvas
        self.canvas.draw()

        size = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumSize(size[0], size[1])


class ElementaryFlowContributionPlot(ContributionPlot):
    def __init__(self, parent=None, *args):
        super(ElementaryFlowContributionPlot, self).__init__(parent, *args)

    def plot(self, mlca, method=None):
        self.ax.clear()
        self.height = 4 + len(mlca.func_units) * 0.3
        self.figure.set_figheight(self.height)

        tc = mlca.top_elementary_flow_contributions(method_name=method, limit=5, relative=True)
        df_tc = pd.DataFrame(tc)
        df_tc.columns = [format_activity_label(a, style='pnl') for a in tc.keys()]
        df_tc.index = [format_activity_label(a, style='bio') for a in df_tc.index]
        plot = df_tc.T.plot.barh(
            stacked=True,
            figsize=(6, 6),
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.rc('legend', **{'fontsize': 8})
        plot.grid(b=False)

        # refresh canvas
        self.canvas.draw()

        size = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumSize(size[0], size[1])