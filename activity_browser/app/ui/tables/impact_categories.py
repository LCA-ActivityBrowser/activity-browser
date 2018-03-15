# -*- coding: utf-8 -*-
import numbers
from PyQt5 import QtWidgets

import brightway2 as bw

from . table import ABTableWidget, ABTableItem
from ...signals import signals


class MethodsTable(ABTableWidget):
    HEADERS = ["Name", "Unit", "# CFs"]
    def __init__(self):
        super(MethodsTable, self).__init__()
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )
        self.connect_signals()
        self.sync()

    def connect_signals(self):
        self.itemDoubleClicked.connect(
            lambda x: signals.method_selected.emit(x.method)
        )
        signals.project_selected.connect(self.sync)

    @ABTableWidget.decorated_sync
    def sync(self, query=None):
        self.setHorizontalHeaderLabels(self.HEADERS)

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
            self.setItem(row, 0, ABTableItem(name, method=method))
            self.setItem(row, 1, ABTableItem(data.get('unit', "Unknown"), method=method))
            num_cfs = data.get('num_cfs', 0)
            self.setItem(row, 2, ABTableItem(str(num_cfs), method=method, number=num_cfs, ))


class CFTable(ABTableWidget):
    COLUMNS = {
        0: "name",
        1: "amount",
        2: "unit",
        3: "uncertain",
    }
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertain"]

    def __init__(self):
        super(CFTable, self).__init__()
        self.setVisible(False)
        self.setColumnCount(len(self.HEADERS))
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )


    @ABTableWidget.decorated_sync
    def sync(self, method):
        self.setHorizontalHeaderLabels(self.HEADERS)
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
            self.setItem(row, 0, ABTableItem(flow['name'], key=key))
            self.setItem(row, 1, ABTableItem(str(flow['categories']), key=key))
            self.setItem(row, 1, ABTableItem(str(flow['categories']), key=key))
            self.setItem(row, 2, ABTableItem("{:.6g}".format(amount), key=key))
            self.setItem(row, 3, ABTableItem(flow.get('unit', 'Unknown'), key=key))
            self.setItem(row, 4, ABTableItem(str(uncertain), key=key))
