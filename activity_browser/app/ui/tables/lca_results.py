# -*- coding: utf-8 -*-
import pandas as pd
from scipy.sparse import csr_matrix
from brightway2 import get_activity

from .dataframe_table import ABDataFrameTable
from PyQt5 import QtCore, QtWidgets

import matplotlib.pyplot as plt
import numpy as np



class LCAResultsTable(ABDataFrameTable):
    @ABDataFrameTable.decorated_sync
    def sync(self, lca):
        col_labels = [" | ".join(x) for x in lca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in lca.func_units]
        self.dataframe = pd.DataFrame(lca.results, index=row_labels, columns=col_labels)


class ProcessContributionsTable(ABDataFrameTable):
    def __init__(self, parent):
        super(ProcessContributionsTable, self).__init__(parent)
        self.parent = parent

    @ABDataFrameTable.decorated_sync
    def sync(self, dummy):
        self.dataframe = self.parent.plot.df_tc

class InventoryCharacterisationTable(ABDataFrameTable):
    def __init__(self, parent):
        super(InventoryCharacterisationTable, self).__init__(parent)
        self.parent = parent

    @ABDataFrameTable.decorated_sync
    def sync(self, dummy):
        self.dataframe = self.parent.plot.df_tc


class InventoryTable(ABDataFrameTable):
    def __init__(self, parent, **kwargs):
        super(InventoryTable, self).__init__(parent, **kwargs)
    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, method=None, limit=1000):
        array = mlca.technosphere_flows[method]
        length = min(limit, len(array))
        labels = [str(get_activity(mlca.rev_activity_dict[i])) for i in range(length)]
        shortlabels = [((i[:98]+'..') if len(i)> 100 else i) for i in labels]
        col_labels = ['Amount']
        row_labels = [i for i in shortlabels[:length]]

        self.dataframe = pd.DataFrame(array[:length], index=row_labels, columns=col_labels)


class BiosphereTable(QtWidgets.QTableView):
    def __init__(self, parent):
        super(BiosphereTable, self).__init__(parent)
    def sync(self, mlca, method=None, limit=100):
        if method is None:
            method = mlca.methods[0]
        matrix = mlca.inventories[method]

        matrix = matrix[:20,:20]

        table = QtWidgets.QTableWidget(self)
        #matrix = csr_matrix([[1,2,3],[5,6,7], [0,9,8], [1,2,3]])

        matrix = matrix.toarray()
        table.setRowCount(matrix.shape[1])
        table.setColumnCount(matrix.shape[0])
        for ni, i in enumerate(matrix):
            for nj, j in enumerate(i):
                table.setItem(nj, ni, QtWidgets.QTableWidgetItem(str(j)))
        table.setVerticalScrollMode(1)
        table.setHorizontalScrollMode(1)
        return table




# class BiosphereTable(ABDataFrameTable):
#     @ABDataFrameTable.decorated_sync
#     def sync(self, mlca, method=None, limit=100):
#         if method is None:
#             method = mlca.methods[0]
#         matrix = mlca.inventories[method]
#         length = limit #min(limit, len(array))
#         labels = [str(get_activity(mlca.rev_activity_dict[i])) for i in range(length)]
#         shortlabels = [((i[:48]+'..') if len(i)> 50 else i) for i in labels]
#         row_labels = [i for i in shortlabels[:length]]
#
#         #self.dataframe = pd.DataFrame(matrix)#, index=row_labels)
#         self.dataframe = pd.DataFrame([[1,2,1],[3,4,9]])
#
#
#




