# -*- coding: utf-8 -*-
from .panel import Panel
from .. import activity_cache
from ..tabs import (
    ActivityDetailsTab,
    HistoryTab,
    LCAResultsTab,
    MethodsTab,
    InventoryTab,
)



class RightPanel(Panel):
    side = "right"

    def __init__(self, *args):
        super(RightPanel, self).__init__(*args)

        self.history_tab = HistoryTab(self)
        # self.inventory_tab = InventoryTabOld(self)
        self.inventory_tab = InventoryTab(self)
        self.methods_tab = MethodsTab(self)
        self.lca_results_tab = LCAResultsTab(self)
        # self.addTab(self.new_inventory_tab, 'New Inventory')
        self.addTab(self.inventory_tab, 'Inventory')

        self.addTab(self.methods_tab, 'Impact Assessment')
        self.addTab(self.history_tab, 'History')

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
