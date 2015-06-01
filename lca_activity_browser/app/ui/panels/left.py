# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..tabs import (
    ActivityDetailsTab,
    CalculationSetupTab,
    CFsTab,
)
from ...signals import signals
from PyQt4 import QtGui


class LeftPanel(QtGui.QTabWidget):
    def __init__(self, parent):
        super(LeftPanel, self).__init__(parent)
        self.setMovable(True)

        self.activity_details_tab = ActivityDetailsTab(self)
        self.cfs_tab = CFsTab(self)
        self.cs_tab = CalculationSetupTab(self)
        self.addTab(self.activity_details_tab, 'Activity')
        self.addTab(self.cfs_tab, 'LCIA CFs')
        self.addTab(self.cs_tab, 'LCA Calculations')

        signals.activity_selected.connect(lambda x: self.select_tab(self.activity_details_tab))

    def select_tab(self, obj):
        self.setCurrentIndex(self.indexOf(obj))
