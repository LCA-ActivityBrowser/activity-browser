# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import seaborn as sns


class Canvas(FigureCanvasQTAgg):
    """A QWidget as well as a Matplotlib (FigureCanvasQTAgg) class.

    Based on http://matplotlib.org/examples/user_interfaces/embedding_in_qt4.html"""
    def __init__(self, parent=None, width=4, height=4, dpi=100, start_axes=True):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        if start_axes:
            self.axes = fig.add_subplot(111)
            # We want the axes cleared every time plot() is called
            self.axes.hold(False)

        self.do_figure()

        super(Canvas, self).__init__(fig)
        self.setParent(parent)
        # If uncommented, fills widget
        # self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        # self.updateGeometry()

    def do_figure(self):
        raise NotImplementedError


class DefaultGraph(FigureCanvasQTAgg):
    # http://web.stanford.edu/~mwaskom/software/seaborn/examples/cubehelix_palette.html
    def __init__(self, parent):
        fig = Figure(figsize=(4, 4), dpi=100, tight_layout=True)
        super(DefaultGraph, self).__init__(fig)
        self.setParent(parent)
        sns.set(style="dark")

        for index, s in zip(range(9), np.linspace(0, 3, 10)):
            axes = fig.add_subplot(3, 3, index + 1)
            x, y = np.random.randn(2, 50)
            cmap = sns.cubehelix_palette(start=s, light=1, as_cmap=True)
            sns.kdeplot(x, y, cmap=cmap, shade=True, cut=5, ax=axes)
            axes.set_xlim(-3, 3)
            axes.set_ylim(-3, 3)
            axes.set_xticks([])
            axes.set_yticks([])

        fig.suptitle("No activity has been selected", y=0.5, fontsize=30, backgroundcolor=(1, 1, 1, 0.5))

        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()


class CorrelationPlot(FigureCanvasQTAgg):
    def __init__(self, parent, data, labels, width=6, height=6, dpi=100):
        figure = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        axes = figure.add_subplot(111)

        super(CorrelationPlot, self).__init__(figure)
        self.setParent(parent)

        sns.set(style="darkgrid")


        cmap = sns.diverging_palette(220, 10, as_cmap=True)
        sns.corrplot(data, names=labels, annot=True, sig_stars=False,
             diag_names=True, cmap=cmap, ax=axes)

        # If uncommented, fills widget
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.updateGeometry()
