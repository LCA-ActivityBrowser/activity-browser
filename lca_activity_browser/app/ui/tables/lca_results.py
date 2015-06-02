# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import get_activity
from PyQt4 import QtCore, QtGui
import itertools


class ReadOnly(QtGui.QTableWidgetItem):
    def __init__(self, *args):
        super(ReadOnly, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)


class LCAResultsTable(QtGui.QTableWidget):
    def sync(self, lca):
        self.clear()

        self.setColumnCount(len(lca.methods))
        self.setRowCount(len(lca.activities))
        col_labels = ["-".join(x) for x in lca.methods]
        row_labels = [str(get_activity(key)) for key, amount in lca.activities]
        self.setHorizontalHeaderLabels(col_labels)
        self.setVerticalHeaderLabels(row_labels)

        for row in range(len(lca.activities)):
            for col in range(len(lca.methods)):
                self.setItem(row, col, ReadOnly("{:.4g}".format(lca.results[row, col])))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
