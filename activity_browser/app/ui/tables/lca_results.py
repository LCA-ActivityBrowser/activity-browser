# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from brightway2 import get_activity, LCA, Database, methods

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
        #lca=LCA({Database('ecoinvent 3.4 cutoff').random(): 1.0}, method=methods.random())
        #array = np.multiply(lca.supply_array, lca.technosphere_matrix.diagonal())
        array = [1,2,3,4,5,6,7,8,9]
        max_length = 4
        length = min(max_length, len(array))
        col_labels = ['tons CO2-eq.']
        row_labels = [str(i) for i in range(len(array))[:length]]
        self.dataframe = pd.DataFrame(array[:length], index=row_labels, columns=col_labels)

        # smooth scrolling instead of jumping from cell to cell
        self.setVerticalScrollMode(1)
        self.setHorizontalScrollMode(1)