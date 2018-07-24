# -*- coding: utf-8 -*-
import pandas as pd
from brightway2 import get_activity

from .dataframe_table import ABDataFrameTable


class LCAResultsTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, lca):
        col_labels = [" | ".join(x) for x in lca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in lca.func_units]
        self.dataframe = pd.DataFrame(lca.results, index=row_labels, columns=col_labels)

        # smooth scrolling instead of jumping from cell to cell
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)


class ProcessContributionsTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, lca):
        col_labels = [] #
        row_labels = []
# How to deal with vastly different top 5's of processes?


class InventoryTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, mlca):
        #col_labels = ['tons CO2-eq.', 'CTUe']
        #row_labels = ["Process 1", "Process 2"]
        self.dataframe = pd.DataFrame(i for i in mlca.lca.inventory) #, index=row_labels, columns=col_labels)

        # smooth scrolling instead of jumping from cell to cell
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)