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
