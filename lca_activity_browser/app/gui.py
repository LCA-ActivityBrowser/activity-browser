# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit

def horizontal_line():
    line = QtGui.QFrame()
    line.setFrameShape(QtGui.QFrame.HLine)
    line.setFrameShadow(QtGui.QFrame.Sunken)
    return line
