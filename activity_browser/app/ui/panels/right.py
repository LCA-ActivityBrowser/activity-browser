# -*- coding: utf-8 -*-
from .panel import Panel, ActivitiesTab, MethodsTab
from ..web.graphnav import GraphNavigatorWidget
from ..web.graphnav import SankeyNavigatorWidget
from ...signals import signals
from .. import activity_cache
from ..tabs import (
    LCASetupTab,
    ActivityDetailsTab,
    ImpactAssessmentTab,
)

class RightPanel(Panel):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        # instantiate tabs
        self.method_panel = MethodsTab(self)
        self.act_panel = ActivitiesTab(self)
        self.LCA_setup_tab = LCASetupTab(self)
        self.lca_results_tab = ImpactAssessmentTab(self)
        self.graph_navigator_tab = GraphNavigatorWidget()

        # add tabs to Panel
        self.addTab(self.LCA_setup_tab, 'LCA Setup')
        self.addTab(self.graph_navigator_tab, 'Graph-Navigator')

        # Signals
        self.connect_signals()

    def connect_signals(self):
        signals.activity_tabs_changed.connect(self.update_activity_panel)
        signals.method_tabs_changed.connect(self.update_method_panel)
        signals.lca_calculation.connect(self.add_Sankey_Widget)
        self.currentChanged.connect(self.calculate_first_sankey)

    def add_Sankey_Widget(self, cs_name):
        print("Adding Sankey Tab")
        if not hasattr(self, "sankey_navigator_tab"):
            self.sankey_navigator_tab = SankeyNavigatorWidget(cs_name)
            self.addTab(self.sankey_navigator_tab, 'LCA Sankey')

    def calculate_first_sankey(self):
        if hasattr(self, "sankey_navigator_tab"):
            if self.currentIndex() == self.indexOf(self.sankey_navigator_tab):
                print("Changed to Sankey Tab")
                self.sankey_navigator_tab.new_sankey()

    def update_method_panel(self):
        if self.method_panel.tab_dict:
            if self.indexOf(self.method_panel) == -1:
                self.addTab(self.method_panel, 'Characterization Factors')
            self.select_tab(self.method_panel)
        else:
            self.removeTab(self.indexOf(self.method_panel))
            self.setCurrentIndex(0)

    def update_activity_panel(self):
        if len(activity_cache):
            self.addTab(self.act_panel, 'Activities')
            # self.select_tab(self.act_panel)
        else:
            self.removeTab(self.indexOf(self.act_panel))
            self.setCurrentIndex(0)


    def close_tab(self, index):
        if index >= 3:
            # TODO: Should look up by tab class, not index, as tabs are movable
            widget = self.widget(index)
            if isinstance(widget, ActivityDetailsTab):
                assert widget.activity in activity_cache
                del activity_cache[widget.activity]
            widget.deleteLater()
            self.removeTab(index)

        self.setCurrentIndex(0)
