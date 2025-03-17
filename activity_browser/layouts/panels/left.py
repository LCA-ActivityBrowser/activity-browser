# -*- coding: utf-8 -*-
from .panel import ABTab
from ..panes.impact_categories import ImpactCategoriesPane
from ..panes.calculation_setups import CalculationSetupsPane


class LeftPanel(ABTab):
    side = "left"

    def __init__(self, *args):
        from ..tabs import HistoryTab, MethodsTab, ProjectTab

        super(LeftPanel, self).__init__(*args)

        self.tabs = {
            "DatabasesPane": ProjectTab(self),
            "Impact Categories": ImpactCategoriesPane(self),
            "Calculation Setups": CalculationSetupsPane(self),
            "History": HistoryTab(self),
        }
        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)
        # tabs hidden at start
        self.hide_tab("History")
