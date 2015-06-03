# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from numbers import Number
from PyQt4 import QtCore, QtGui
from ...signals import signals


class MethodItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, method=None):
        super(MethodItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.method = method


class Number(QtGui.QTableWidgetItem):
    def __init__(self, *args, method=None, number=None):
        super(Number, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.number = number
        self.method = method

    def __lt__(self, other):
        if isinstance(other, Number):
            return self.number < other.number
        return super(Number, self).__lt__(other)


class MethodsTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(MethodsTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setDragEnabled(True)
        self.setSortingEnabled(True)
        self.setHorizontalHeaderLabels(["Name", "Unit", "# CFs"])
        self.sync()
        self.itemDoubleClicked.connect(
            lambda x: signals.method_selected.emit(x.method)
        )

    def sync(self, query=None):
        self.clear()
        self.setHorizontalHeaderLabels(["Name", "Unit", "# CFs"])

        sorted_names = sorted([(", ".join(method), method) for method in methods])

        if query:
            sorted_names = [
                obj for obj in sorted_names
                if query.lower() in obj[0].lower()
            ]

        self.setRowCount(len(sorted_names))
        for row, method_obj in enumerate(sorted_names):
            name, method = method_obj
            data = methods[method]
            self.setItem(row, 0, MethodItem(name, method=method))
            self.setItem(row, 1, MethodItem(data.get('unit', "Unknown"), method=method))
            num_cfs = data.get('num_cfs', 0)
            self.setItem(row, 2, Number(str(num_cfs), method=method, number=num_cfs))

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
