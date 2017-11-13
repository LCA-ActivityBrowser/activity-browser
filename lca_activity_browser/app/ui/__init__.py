# -*- coding: utf-8 -*-
# from __future__ import print_function, unicode_literals
# from eight import *

from PyQt5 import QtGui, QtWidgets

bold_font = QtGui.QFont()
bold_font.setBold(True)
bold_font.setPointSize(16)

activity_cache = {}


def horizontal_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line

def header(label):
    label = QtWidgets.QLabel(label)
    label.setFont(bold_font)
    return label
