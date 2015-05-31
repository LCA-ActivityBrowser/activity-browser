# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..tabs import (
    InventoryTab,
    MethodsTab,
)
from PyQt4 import QtGui


class RightPanel(QtGui.QTabWidget):
    def __init__(self, parent):
        super(RightPanel, self).__init__(parent)
        self.setMovable(True)

        self.inventory_tab = InventoryTab(self)
        self.methods_tab = MethodsTab(self)
        self.addTab(self.inventory_tab, 'Inventory')
        self.addTab(self.methods_tab, 'Impact Assessment')
