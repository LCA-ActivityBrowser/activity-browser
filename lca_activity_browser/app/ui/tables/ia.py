# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from brightway2 import *
from PyQt5 import QtCore, QtGui, QtWidgets
import numbers


class MethodItem(QtWidgets.QTableWidgetItem):
    def __init__(self, method, *args):
        super(MethodItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.method = method


class Number(QtWidgets.QTableWidgetItem):
    def __init__(self, method, number, *args):
        super(Number, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.number = number
        self.method = method

    def __lt__(self, other):
        if isinstance(other, Number):
            return self.number < other.number
        return super(Number, self).__lt__(other)


class MethodsTableWidget(QtWidgets.QTableWidget):
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
            self.setItem(row, 0, MethodItem(method, name))
            self.setItem(row, 1, MethodItem(method, data.get('unit', "Unknown")))
            num_cfs = data.get('num_cfs', 0)
            self.setItem(row, 2, Number(method, num_cfs, str(num_cfs)))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class CFItem(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(CFItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class CFsTableWidget(QtWidgets.QTableWidget):
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
            if isinstance(amount, numbers.Number):
                uncertain = "False"
            else:
                uncertain = "True"
                amount = amount['amount']
            self.setItem(row, 0, CFItem(key, flow['name']))
            self.setItem(row, 1, CFItem(key, "{:.6g}".format(amount)))
            self.setItem(row, 2, CFItem(key, flow.get('unit', 'Unknown')))
            self.setItem(row, 3, CFItem(key, uncertain))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
