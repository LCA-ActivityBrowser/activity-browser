# -*- coding: utf-8 -*-
from ...signals import signals
from . table import ActivityBrowserTableWidget
import brightway2 as bw
from PyQt5 import QtCore, QtWidgets
import numbers


class MethodItem(QtWidgets.QTableWidgetItem):
    def __init__(self, method, *args):
        super(MethodItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.method = method


class NumberItem(QtWidgets.QTableWidgetItem):
    def __init__(self, method, number, *args):
        super(NumberItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.number = number
        self.method = method

    def __lt__(self, other):
        if isinstance(other, NumberItem):
            return self.number < other.number
        return super(NumberItem, self).__lt__(other)


class MethodsTable(ActivityBrowserTableWidget):
    def __init__(self):
        super(MethodsTable, self).__init__()
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

        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])

        if query:
            sorted_names = [
                obj for obj in sorted_names
                if query.lower() in obj[0].lower()
            ]

        self.setRowCount(len(sorted_names))
        for row, method_obj in enumerate(sorted_names):
            name, method = method_obj
            data = bw.methods[method]
            self.setItem(row, 0, MethodItem(method, name))
            self.setItem(row, 1, MethodItem(method, data.get('unit', "Unknown")))
            num_cfs = data.get('num_cfs', 0)
            self.setItem(row, 2, NumberItem(method, num_cfs, str(num_cfs)))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class CFItem(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(CFItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class CFTable(ActivityBrowserTableWidget):
    COLUMNS = {
        0: "name",
        1: "amount",
        2: "unit",
        3: "uncertain",
    }

    def __init__(self):
        super(CFTable, self).__init__()
        self.setVisible(False)
        self.setColumnCount(4)
        self.setSortingEnabled(True)
        self.setHorizontalHeaderLabels(["Name", "Amount", "Unit", "Uncertain"])

    def sync(self, method):
        method = bw.Method(method)
        data = method.load()
        self.setRowCount(len(data))
        for row, obj in enumerate(data):
            key, amount = obj[:2]
            flow = bw.get_activity(key)
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
