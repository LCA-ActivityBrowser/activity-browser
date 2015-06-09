# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ..tables import ActivitiesHistoryWidget
from PyQt4 import QtGui, QtCore


class HistoryTab(QtGui.QWidget):
    def __init__(self, parent=None):
        super(HistoryTab, self).__init__(parent)
        self.layout = QtGui.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addWidget(header("Activity selection history:"))
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(ActivitiesHistoryWidget(self))
        self.setLayout(self.layout)
