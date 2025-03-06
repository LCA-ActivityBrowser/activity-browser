# -*- coding: utf-8 -*-
from .panel import ABTab
from ..panes.impact_categories import ImpactCategories


class LeftPanel(ABTab):
    side = "left"

    def __init__(self, *args):
        from ..tabs import HistoryTab, MethodsTab, ProjectTab

        super(LeftPanel, self).__init__(*args)

        self.tabs = {
            "Databases": ProjectTab(self),
            "Impact Categories": ImpactCategories(self),
            "History": HistoryTab(self),
        }
        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)
        # tabs hidden at start
        self.hide_tab("History")
