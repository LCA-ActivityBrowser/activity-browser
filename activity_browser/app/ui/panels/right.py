# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtWidgets import QVBoxLayout

from activity_browser import PACKAGE_DIRECTORY
from .panel import ABTab
from ..web.webutils import RestrictedWebViewWidget
from ..web.graphnav import GraphNavigatorWidget
from ..tabs import (
    LCASetupTab,
    LCAResultsTab,
    CharacterizationFactorsTab,
    ActivitiesTab,
    ParametersTab
)
from ...signals import signals
from ...bwutils.commontasks import get_activity_name


class RightPanel(ABTab):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.tabs = {
            "Welcome": RestrictedWebViewWidget(html_file=PACKAGE_DIRECTORY + r'/app/ui/web/startscreen/welcome.html'),
            "Characterization Factors": CharacterizationFactorsTab(self),
            "Activities": ActivitiesTab(self),
            "LCA Setup": LCASetupTab(self),
            "Graph Explorer": GraphExplorerTab(self),
            "LCA results": LCAResultsTab(self),
            "Parameters": ParametersTab(self),
        }
        self.tab_order = {}

        for tab_name, tab in self.tabs.items():
            self.tab_order[tab_name] = self.addTab(tab, tab_name)

        # tabs hidden at start
        for tab_name in ["Activities", "Characterization Factors", "Graph Explorer", "LCA results"]:
            self.hide_tab(tab_name)

    def show_tab(self, tab_name):
        """ Re-inserts tab at the initial location.

        This avoids constantly re-ordering the mayor tabs.
        """
        if tab_name in self.tabs:
            tab = self.tabs[tab_name]
            print("+showing tab:", tab_name)
            tab.setVisible(True)
            self.insertTab(self.tab_order[tab_name], tab, tab_name)
            self.select_tab(tab)


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
        signals.open_activity_graph_tab.connect(self.add_tab)

    def add_tab(self, key, select=True):
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            print("adding graph tab")
            new_tab = GraphNavigatorWidget(self, key=key)
            self.tabs[key] = new_tab
            self.addTab(new_tab, get_activity_name(bw.get_activity(key), str_length=30))
        else:
            tab = self.tabs[key]
            tab.new_graph(key)

        if select:
            self.select_tab(self.tabs[key])
            signals.show_tab.emit("Graph Explorer")
