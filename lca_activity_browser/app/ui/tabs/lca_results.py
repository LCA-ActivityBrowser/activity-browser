# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
# from ..tables import ActivitiesHistoryWidget
from PyQt4 import QtGui, QtCore
from bw2calc.multi_lca import MultiLCA
from ...signals import signals
from ..graphics import CorrelationPlot


class LCAResultsTab(QtGui.QWidget):
    def __init__(self, parent):
        super(LCAResultsTab, self).__init__(parent)
        self.tab = parent
        self.visible = False

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)

    def add_tab(self):
        self.tab.addTab(self, "LCA Results")
        self.tab.select_tab(self)
        self.visible = True

    def remove_tab(self):
        if self.visible:
            self.tab.removeTab(4)
            self.visible = False
            self.corr_chart.deleteLater()

    def calculate(self, name):
        self.lca = MultiLCA(name)
        labels = [str(x + 1) for x in range(len(self.lca.activities))]
        normalized_results = self.lca.results / self.lca.results.max(axis=0)
        self.corr_chart = CorrelationPlot(self, normalized_results.T, labels)
        self.layout.addWidget(self.corr_chart)
        self.add_tab()
