# -*- coding: utf-8 -*-
import pandas as pd
from brightway2 import get_activity

from .dataframe_table import ABDataFrameTable
from PyQt5 import QtWidgets

from operator import itemgetter

from scipy.sparse import csr_matrix


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

def inventory_labels(length, mlca, labellength):
    labels = [str(get_activity(mlca.rev_activity_dict[i])) for i in range(length)]
    shortlabels = [((i[:labellength-2] + '..') if len(i) > labellength else i) for i in labels]
    return shortlabels

class InventoryTable(ABDataFrameTable):
    def __init__(self, parent, **kwargs):
        super(InventoryTable, self).__init__(parent, **kwargs)
    @ABDataFrameTable.decorated_sync
    def sync(self, mlca, method=None, limit=100):

        if method not in mlca.technosphere_flows.keys():
            method = mlca.func_unit_translation_dict[str(method)]

        array = mlca.technosphere_flows[str(method)]
        length = min(limit, len(array))
        shortlabels= inventory_labels(length, mlca, 100)

        array, shortlabels = (list(t) for t in zip(*reversed(sorted(zip(array, shortlabels)))))

        data_tuples = [
            (float(i), shortlabels[n])
            for n, i in enumerate(array)]

        ordered_data = (sorted(data_tuples, key=itemgetter(0), reverse=True))
        array = [i[0] for i in ordered_data]
        shortlabels = [i[1] for i in ordered_data]

        col_labels = ['Amount']
        row_labels = [i for i in shortlabels[:length]]

        self.dataframe = pd.DataFrame(array[:length], index=row_labels, columns=col_labels)



class BiosphereTable(QtWidgets.QTableView):
    def __init__(self, parent):
        super(BiosphereTable, self).__init__(parent)
    def sync(self, mlca, method=None, limit=20):

        if method not in mlca.technosphere_flows.keys():
            method = mlca.func_unit_translation_dict[str(method)]

        matrix = mlca.inventories[str(method)]
        matrix = matrix[:limit, :limit]

        table = QtWidgets.QTableWidget(self)
        #matrix = csr_matrix([[1,2,3],[5,6,7], [0,9,8], [1,2,3]])

        matrix = matrix.toarray()
        table.setRowCount(matrix.shape[1])
        table.setColumnCount(matrix.shape[0])
        for ni, i in enumerate(matrix):
            for nj, j in enumerate(i):
                table.setItem(nj, ni, QtWidgets.QTableWidgetItem(str(j)))
        length = limit
        shortlabels= inventory_labels(length, mlca, 50)
        table.setVerticalHeaderLabels(shortlabels)
        table.setVerticalScrollMode(1)
        table.setHorizontalScrollMode(1)
        table.setMinimumWidth(700)

        return table






