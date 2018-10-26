# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5.QtWidgets import QVBoxLayout

from .panel import ABTab
from ..web.graphnav import GraphNavigatorWidget
from ..tabs import (
    LCASetupTab,
    LCAResultsTab,
    CharacterizationFactorsTab,
    ActivitiesTab
)
from ...signals import signals
from ...bwutils.commontasks import get_activity_name


class RightPanel(ABTab):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.tabs = {
            "Characterization Factors": CharacterizationFactorsTab(self),
            "Activities": ActivitiesTab(self),
            "LCA Setup": LCASetupTab(self),
            "Graph Explorer": GraphExplorerTab(self),
            "LCA results": LCAResultsTab(self),
        }

        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)

        # tabs hidden at start
        for tab_name in ["Activities", "Characterization Factors", "Graph Explorer", "LCA results"]:
            self.hide_tab(tab_name)


class GraphExplorerTab(ABTab):
    def __init__(self, parent):
        super(GraphExplorerTab, self).__init__(parent)

        self.setMovable(True)
        self.setTabsClosable(True)
        # self.setTabShape(1)  # Triangular-shaped Tabs

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        self.tabCloseRequested.connect(self.close_tab)
        signals.project_selected.connect(self.close_all)
        # signals.show_tab.connect(self.add_first_tab)
        signals.open_activity_graph_tab.connect(self.add_tab)

    # def add_first_tab(self):
    #     if not self.tabs:
    #         self.add_tab("empty", select=False)

    def add_tab(self, key, select=True):
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            print("adding graph tab")
            new_tab = GraphNavigatorWidget(self, key=key)
            # new_tab = GraphNavigatorWidget(self)
            # new_tab.new_graph(key)
            self.tabs[key] = new_tab
            self.addTab(new_tab, get_activity_name(bw.get_activity(key), str_length=30))
            # new_tab.new_graph(key)
        else:
            tab = self.tabs[key]
            tab.new_graph(key)

        if select:
            self.select_tab(self.tabs[key])
            signals.show_tab.emit("Graph Explorer")


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