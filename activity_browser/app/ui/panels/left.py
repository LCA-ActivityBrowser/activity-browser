# -*- coding: utf-8 -*-
from .panel import Panel, ActivitiesPanel
from .. import activity_cache
from ..graphics import DefaultGraph
from ..tabs import CalculationSetupTab, CFsTab
from ...signals import signals


class LeftPanel(Panel):
    side = "left"

    def __init__(self, *args):
        super(LeftPanel, self).__init__(*args)

        self.chart_tab = DefaultGraph(self)
        self.cfs_tab = CFsTab(self)
        self.cs_tab = CalculationSetupTab(self)
        self.act_panel = ActivitiesPanel(self)
        self.addTab(self.chart_tab, 'Splash screen')
        self.addTab(self.cfs_tab, 'LCIA CFs')
        self.addTab(self.cs_tab, 'LCA Calculations')

        signals.activity_tabs_changed.connect(self.update_activity_panel)

    def update_activity_panel(self):
        if len(activity_cache):
            self.addTab(self.act_panel, 'Activities')
            self.select_tab(self.act_panel)
        else:
            self.removeTab(self.indexOf(self.act_panel))
            self.setCurrentIndex(0)
