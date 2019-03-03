# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from brightway2 import get_activity

from .dataframe_table import ABDataFrameTable


class LCAResultsTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, relative=False):
        if relative:
            data = mlca.results_normalized
        else:
            data = mlca.results
        col_labels = [" | ".join(x) for x in mlca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in mlca.func_units]
        self.dataframe = pd.DataFrame(data, index=row_labels, columns=col_labels)


class InventoryTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, df):
        self.dataframe = df
        # sort ignoring case sensitivity
        # self.dataframe = self.dataframe.iloc[self.dataframe["name"].str.lower().argsort()]
        # self.dataframe.reset_index(inplace=True, drop=True)


class ContributionTable(ABDataFrameTable):
    def __init__(self, parent):
        super(ContributionTable, self).__init__(parent)
        self.parent = parent
        self.dataframe = None

    @ABDataFrameTable.decorated_sync
    def sync(self):
        self.dataframe = self.parent.df.replace(np.nan, '', regex=True)  # replace 'nan' values with emtpy string








