# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import horizontal_line, header
from ..tables import ActivitiesHistoryWidget
from ..tabs import (
    InventoryTab,
    LCAResultsTab,
    MethodsTab,
)
from PyQt4 import QtGui, QtCore


class RightPanel(QtGui.QTabWidget):
    def __init__(self, parent):
        super(RightPanel, self).__init__(parent)
        self.setMovable(True)

        self.history_tab = self.get_history_tab()
        self.inventory_tab = InventoryTab(self)
        self.methods_tab = MethodsTab(self)
        self.lca_results_tab = LCAResultsTab(self)
        self.addTab(self.inventory_tab, 'Inventory')
        self.addTab(self.methods_tab, 'Impact Assessment')
        self.addTab(self.history_tab, 'History')

    def get_history_tab(self):
        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header("Activity selection history:"))
        layout.addWidget(horizontal_line())
        layout.addWidget(ActivitiesHistoryWidget(self))

        tab = QtGui.QWidget(self)
        tab.setLayout(layout)
        return tab

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))
