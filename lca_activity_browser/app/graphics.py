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
    def __init__(self, parent=None, width=4, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
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
        sns.set(style="dark")
        x, y = np.random.randn(2, 50)
        cmap = sns.cubehelix_palette(start=3., light=1, as_cmap=True)
        sns.kdeplot(x, y, cmap=cmap, shade=True, cut=5, ax=self.axes)
        self.axes.set_xlim(-3, 3)
        self.axes.set_ylim(-3, 3)

        # rs = np.random.RandomState(10)
        # b, g, r, p = sns.color_palette("muted", 4)
        # d = rs.normal(size=100)
        # sns.distplot(d, color=b, ax=self.axes)
        # t = np.arange(0.0, 3.0, 0.01)
        # s = np.sin(2*np.pi*t)
        # self.axes.plot(t, s)

# class DynamicRandom(Canvas):
#     def __init__(self, *args, **kwargs):
#         super(DynamicRandom, self).__init__(*args, **kwargs)
#         timer = QtCore.QTimer(self)
#         timer.timeout.connect(self.update_figure)
#         timer.start(1000)

#     def do_figure(self):
#         pass

# #!/usr/bin/env python

# # embedding_in_qt4.py --- Simple Qt4 application embedding matplotlib canvases
# #
# # Copyright (C) 2005 Florent Rougon
# #               2006 Darren Dale
# #
# # This file is an example program for matplotlib. It may be used and
# # modified with no restriction; raw copies as well as modified versions
# # may be distributed without limitation.

# from __future__ import unicode_literals
# import sys
# import os
# import random
# from matplotlib.backends import qt4_compat
# use_pyside = qt4_compat.QT_API == qt4_compat.QT_API_PYSIDE
# if use_pyside:
#     from PySide import QtGui, QtCore
# else:
#     from PyQt4 import QtGui, QtCore

# from numpy import arange, sin, pi
# from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

# progname = os.path.basename(sys.argv[0])
# progversion = "0.1"


# class Canvas(FigureCanvasQTAgg):
#     """A QWidget as well as a Matplotlib (FigureCanvasQTAgg) class."""
#     def __init__(self, parent=None, width=4, height=4, dpi=100):
#         fig = Figure(figsize=(width, height), dpi=dpi)
#         self.axes = fig.add_subplot(111)
#         # We want the axes cleared every time plot() is called
#         self.axes.hold(False)

#         self.compute_initial_figure()

#         #
#         FigureCanvas.__init__(self, fig)
#         self.setParent(parent)

#         FigureCanvas.setSizePolicy(self,
#                                    QtGui.QSizePolicy.Expanding,
#                                    QtGui.QSizePolicy.Expanding)
#         FigureCanvas.updateGeometry(self)

#     def compute_initial_figure(self):
#         pass


# class MyStaticMplCanvas(MyMplCanvas):
#     """Simple canvas with a sine plot."""
#     def compute_initial_figure(self):
#         t = arange(0.0, 3.0, 0.01)
#         s = sin(2*pi*t)
#         self.axes.plot(t, s)


# class MyDynamicMplCanvas(MyMplCanvas):
#     """A canvas that updates itself every second with a new plot."""
#     def __init__(self, *args, **kwargs):
#         MyMplCanvas.__init__(self, *args, **kwargs)
#         timer = QtCore.QTimer(self)
#         timer.timeout.connect(self.update_figure)
#         timer.start(1000)

#     def compute_initial_figure(self):
#         self.axes.plot([0, 1, 2, 3], [1, 2, 0, 4], 'r')

#     def update_figure(self):
#         # Build a list of 4 random integers between 0 and 10 (both inclusive)
#         l = [random.randint(0, 10) for i in range(4)]

#         self.axes.plot([0, 1, 2, 3], l, 'r')
#         self.draw()






#         self.main_widget = QtGui.QWidget(self)

#         l = QtGui.QVBoxLayout(self.main_widget)
#         sc = MyStaticMplCanvas(self.main_widget, width=5, height=4, dpi=100)
#         dc = MyDynamicMplCanvas(self.main_widget, width=5, height=4, dpi=100)
#         l.addWidget(sc)
#         l.addWidget(dc)

