# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5.QtWidgets import QVBoxLayout

from .panel import ABTab
from ..web.webutils import RestrictedWebViewWidget
from ..web.graphnav import GraphNavigatorWidget
from ..tabs import (
    LCASetupTab,
    LCAResultsTab,
    CharacterizationFactorsTab,
    ActivitiesTab,
    ParametersTab,
)
from ...signals import signals
from ...bwutils.commontasks import get_activity_name
from .... import PACKAGE_DIRECTORY


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

        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)

        # tabs hidden at start
        for tab_name in ["Activities", "Characterization Factors", "Graph Explorer", "LCA results"]:
            self.hide_tab(tab_name)

        # self.connect_signals()

    # def connect_signals(self):
    #     self.currentChanged.connect(
    #         lambda i, x="Welcome": self.hide_tab(x, current_index=i)
    #     )

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
