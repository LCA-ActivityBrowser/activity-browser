# -*- coding: utf-8 -*-
from brightway2 import get_activity
from PyQt5 import QtCore, QtWidgets

from . table import ABTableWidget


class ReadOnlyItem(QtWidgets.QTableWidgetItem):
    def __init__(self, *args):
        super(ReadOnlyItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)


class LCAResultsTable(ABTableWidget):
    """ Displays total LCA scores for multiple functional units and LCIA methods. """

    @ABTableWidget.decorated_sync
    def sync(self, lca):
        self.setColumnCount(len(lca.methods))
        self.setRowCount(len(lca.func_units))

        col_labels = ["-".join(x) for x in lca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in lca.func_units]
        self.setHorizontalHeaderLabels(col_labels)
        self.setVerticalHeaderLabels(row_labels)

        for row in range(len(lca.func_units)):
            for col in range(len(lca.methods)):
                self.setItem(row, col, ReadOnlyItem("{:.4g}".format(lca.results[row, col])))

        # ensure minimum height as it gets too small otherwise
        self.setMinimumHeight(self.rowHeight(0) * (self.rowCount()) + self.autoScrollMargin())
