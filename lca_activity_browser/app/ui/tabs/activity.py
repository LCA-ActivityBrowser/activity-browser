# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ...signals import signals
from PyQt4 import QtCore, QtGui
from ...graphics import Canvas


class ActivityDetailsTab(QtGui.QWidget):
    def __init__(self, parent):
        super(ActivityDetailsTab, self).__init__(parent)
        self.window = parent

        self.no_activity_label = QtGui.QLabel('No activity selected yet')
        self.no_consumption_label = QtGui.QLabel("No activities consume the reference product of this activity.")
        self.no_consumption_label.hide()

        self.chart1 = Canvas()
        self.chart2 = Canvas()

        activity_container = QtGui.QVBoxLayout()
        activity_container.setAlignment(QtCore.Qt.AlignTop)
        activity_container.addWidget(self.no_activity_label)
        activity_container.addWidget(self.no_consumption_label)
        activity_container.addWidget(self.chart1)
        activity_container.addWidget(self.chart2)
        self.setLayout(activity_container)

        signals.project_changed.connect(self.get_focus)

    def get_focus(self, name):
        self.window.select_tab(self, "left")
