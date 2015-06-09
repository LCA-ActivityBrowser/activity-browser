# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..graphics import DefaultGraph
from ..tabs import (
    CalculationSetupTab,
    CFsTab,
)
from ...signals import signals
from .panel import Panel


class LeftPanel(Panel):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)

        self.chart_tab = DefaultGraph(self)
        self.cfs_tab = CFsTab(self)
        self.cs_tab = CalculationSetupTab(self)
        self.addTab(self.chart_tab, 'Splash screen')
        self.addTab(self.cfs_tab, 'LCIA CFs')
        self.addTab(self.cs_tab, 'LCA Calculations')
