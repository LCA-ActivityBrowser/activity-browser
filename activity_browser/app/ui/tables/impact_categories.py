# -*- coding: utf-8 -*-
import numbers

import brightway2 as bw
import pandas as pd
from PyQt5 import QtWidgets

from activity_browser.app.signals import signals

from .table import ABTableWidget, ABTableItem
from .views import ABDataFrameView, dataframe_sync


class MethodsTable(ABDataFrameView):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_model = True
        self.setDragEnabled(True)
        self.setDragDropMode(ABDataFrameView.DragOnly)
        self.sync()
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(self.method_selected)
        signals.project_selected.connect(self.sync)

    def method_selected(self, proxy):
        index = self.get_source_index(proxy)
        method = self.dataframe.iloc[index.row(), ]["method"]
        signals.method_selected.emit(method)

    def selectedItems(self) -> list:
        """ Use to retrieve the method objects for the selected rows.

        NOTE: Shadows the `selectedItems` method in QTableWidget as it is used
        by `CSMethodsTable`. Possibly remove or improve in the future.
        """
        indexes = [self.get_source_index(p) for p in self.selectedIndexes()]
        return [
            self.dataframe.iloc[index.row(), ] for index in indexes
        ]

    @dataframe_sync
    def sync(self, query=None):
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])

        if query:
            sorted_names = filter(
                lambda obj: query.lower() in obj[0].lower(), sorted_names
            )

        data = []
        for method_obj in sorted_names:
            method = bw.methods[method_obj[1]]
            row =  {
                "Name": method_obj[0],
                "Unit": method.get("unit", "Unknown"),
                "# CFs": str(method.get("num_cfs", 0)),
                "method": method_obj[1],
            }
            data.append(row)
        self.dataframe = pd.DataFrame(data, columns=self.HEADERS)

    def _resize(self):
        self.setColumnHidden(3, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))


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
