# -*- coding: utf-8 -*-
from .panel import ABTab
from ..web.graphnav import GraphNavigatorWidget
from ..tabs import (
    LCASetupTab,
    LCAResultsTab,
    CharacterizationFactorsTab,
    ActivitiesTab
)


class RightPanel(ABTab):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.tabs = {
            "Characterization Factors": CharacterizationFactorsTab(self),
            "Activities": ActivitiesTab(self),
            "LCA Setup": LCASetupTab(self),
            "Graph Explorer": GraphNavigatorWidget(),
            "LCA results": LCAResultsTab(self),
        }

        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)

        # tabs hidden at start
        for tab_name in ["Activities", "Characterization Factors", "Graph Explorer", "LCA results"]:
            self.hide_tab(tab_name)





# Delete once Sankey stuff has been resolved

        # signals.lca_calculation.connect(self.add_Sankey_Widget)
        # self.currentChanged.connect(self.calculate_first_sankey)

    # def add_Sankey_Widget(self, cs_name):
    #     print("Adding Sankey Tab")
    #     # if not hasattr(self, "sankey_navigator_tab"):
    #     self.sankey_navigator_tab = SankeyNavigatorWidget(cs_name)
    #     self.addTab(self.sankey_navigator_tab, 'LCA Sankey')

    # def calculate_first_sankey(self):
    #     if hasattr(self, "sankey_navigator_tab"):
    #         if self.currentIndex() == self.indexOf(self.sankey_navigator_tab):
    #             print("Changed to Sankey Tab")
    #             if not self.sankey_navigator_tab.graph.json_data:
    #                 print("Calculated first Sankey")
    #                 self.sankey_navigator_tab.new_sankey()