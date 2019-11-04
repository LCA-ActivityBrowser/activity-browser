# -*- coding: utf-8 -*-
import numbers

import brightway2 as bw
from pandas import DataFrame
from PySide2 import QtWidgets

from activity_browser.app.signals import signals

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
        self.dataframe = DataFrame(data, columns=self.HEADERS)

    def _resize(self):
        self.setColumnHidden(3, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))


class CFTable(ABDataFrameView):
    COLUMNS = [
        "name",
        "categories",
        "amount",
        "unit",
        "uncertain",
    ]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertain"] + ["key"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

    @dataframe_sync
    def sync(self, method: tuple) -> None:
        method = bw.Method(method)
        method_data = method.load()
        data = []
        for obj in method_data:
            key, amount = obj[:2]
            flow = bw.get_activity(key)
            if isinstance(amount, numbers.Number):
                uncertain = "False"
            else:
                uncertain = "True"
                amount = amount['amount']
            row = {
                self.HEADERS[i]: flow.get(self.COLUMNS[i])
                for i in range(len(self.COLUMNS))
            }
            row.update({"Amount": amount, "Uncertain": uncertain, "key": key})
            data.append(row)
        self.dataframe = DataFrame(data, columns=self.HEADERS)

    def _resize(self):
        self.setColumnHidden(5, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))
