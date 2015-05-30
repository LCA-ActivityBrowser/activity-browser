# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from bw2data.utils import natural_sort
from numbers import Number
from PyQt4 import QtCore, QtGui


class MethodItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, method=None):
        super(MethodItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.method = method


class MethodsTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(MethodsTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Unit", "# CFs"])
        self.sync()

    def sync(self):
        self.setRowCount(len(methods))
        for row, method in enumerate(sorted(methods, key=lambda x: ("".join(x)).lower())):
            data = methods[method]
            self.setItem(row, 0, MethodItem(", ".join(method), method=method))
            self.setItem(row, 1, MethodItem(data.get('unit', "Unknown"), method=method))
            self.setItem(row, 2, MethodItem(data.get('num_cfs', 'Unknown'), method=method))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class CFItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, key=None):
        super(CFItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class CFsTableWidget(QtGui.QTableWidget):
    COLUMNS = {
        0: "name",
        1: "amount",
        2: "unit",
        3: "uncertain",
    }

    def __init__(self):
        super(CFsTableWidget, self).__init__()
        self.setVisible(False)
        self.setColumnCount(4)
        self.setSortingEnabled(True)
        self.setHorizontalHeaderLabels(["Name", "Amount", "Unit", "Uncertain"])

    def sync(self, method):
        method = Method(method)
        data = method.load()
        self.setRowCount(len(data))
        for row, obj in enumerate(data):
            key, amount = obj[:2]
            flow = get_activity(key)
            if isinstance(amount, Number):
                uncertain = "False"
            else:
                uncertain = "True"
                amount = amount['amount']
            self.setItem(row, 0, CFItem(flow['name'], key=key))
            self.setItem(row, 1, CFItem("{:.6g}".format(amount), key=key))
            self.setItem(row, 2, CFItem(flow.get('unit', 'Unknown'), key=key))
            self.setItem(row, 3, CFItem(uncertain, key=key))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
