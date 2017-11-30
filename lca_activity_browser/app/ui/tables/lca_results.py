# -*- coding: utf-8 -*-
from brightway2 import get_activity
from PyQt5 import QtCore, QtWidgets


class ReadOnly(QtWidgets.QTableWidgetItem):
    def __init__(self, *args):
        super(ReadOnly, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)


class LCAResultsTable(QtWidgets.QTableWidget):
    def sync(self, lca):
        self.clear()

        self.setSortingEnabled(True)
        self.setColumnCount(len(lca.methods))
        self.setRowCount(len(lca.func_units))
        col_labels = ["-".join(x) for x in lca.methods]
        row_labels = [str(get_activity(list(func_unit.keys())[0])) for func_unit in lca.func_units]
        self.setHorizontalHeaderLabels(col_labels)
        self.setVerticalHeaderLabels(row_labels)

        for row in range(len(lca.func_units)):
            for col in range(len(lca.methods)):
                self.setItem(row, col, ReadOnly("{:.4g}".format(lca.results[row, col])))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        # self.setMinimumHeight(self.maximumHeight())
        # self.setMinimumHeight(500)
        # self.setMinimumHeight(self.frameGeometry().height())
        self.setMinimumHeight(self.sizeHint().height())
