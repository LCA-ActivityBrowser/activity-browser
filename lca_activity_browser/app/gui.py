# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit

bold_font = QtGui.QFont()
bold_font.setBold(True)
bold_font.setPointSize(12)


def horizontal_line():
    line = QtGui.QFrame()
    line.setFrameShape(QtGui.QFrame.HLine)
    line.setFrameShadow(QtGui.QFrame.Sunken)
    return line

def header(label):
    label = QtGui.QLabel(label)
    label.setFont(bold_font)
    return label
