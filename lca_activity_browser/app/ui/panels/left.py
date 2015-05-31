# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..tabs import (
    ActivityDetailsTab,
    CalculationSetupTab,
    CFsTab,
)
from PyQt4 import QtGui


class LeftPanel(QtGui.QTabWidget):
    def __init__(self, parent):
        super(LeftPanel, self).__init__(parent)
        self.setMovable(True)

        self.activity_tab = ActivityDetailsTab(self)
        self.cfs_tab = CFsTab(self)
        self.cs_tab = CalculationSetupTab(self)
        self.addTab(self.activity_tab, 'Activity')
        self.addTab(self.cfs_tab, 'LCIA CFs')
        self.addTab(self.cs_tab, 'LCA Calculations')
