# -*- coding: utf-8 -*-
import numbers

import brightway2 as bw
from pandas import DataFrame
from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot

from ...signals import signals
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

    @Slot(QModelIndex, name="methodSelection")
    def method_selected(self, proxy):
        index = self.get_source_index(proxy)
        method = self.dataframe.iloc[index.row(), ]["method"]
        signals.method_selected.emit(method)

    def selectedItems(self) -> list:
        """ Use to retrieve the method objects for the selected rows.

        TODO: Shadows the `selectedItems` method in QTableWidget as it is used
         by `CSMethodsTable`. Possibly remove or improve in the future.
        """
        indexes = (self.get_source_index(p) for p in self.selectedIndexes())
        return [
            self.dataframe.iloc[index.row(), ] for index in indexes
        ]

    @dataframe_sync
    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        if query:
            sorted_names = filter(
                lambda obj: query.lower() in obj[0].lower(), sorted_names
            )
        self.dataframe = DataFrame([
            self.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)

    def build_row(self, method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }

    def _resize(self) -> None:
        self.setColumnHidden(self.dataframe.columns.get_loc("method"), True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))


class CFTable(ABDataFrameView):
    COLUMNS = ["name", "categories", "amount", "unit", "uncertain"]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertain"] + ["key"]
    UNCERTAINTY = [
        "uncertainty type", "loc", "scale", "shape", "minimum", "maximum"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

    @dataframe_sync
    def sync(self, method: tuple) -> None:
        method = bw.Method(method)
        method_data = method.load()
        self.dataframe = DataFrame([
            self.build_row(obj) for obj in method_data
        ], columns=self.HEADERS)

    def build_row(self, method_cf) -> dict:
        key, amount = method_cf[:2]
        flow = bw.get_activity(key)
        row = {
            self.HEADERS[i]: flow.get(c) for i, c in enumerate(self.COLUMNS)
        }
        # If uncertain, unpack the uncertainty dictionary
        uncertain = not isinstance(amount, numbers.Number)
        if uncertain:
            row.update({k: amount.get(k, "nan") for k in self.UNCERTAINTY})
            amount = amount["amount"]
        row.update({"Amount": amount, "Uncertain": uncertain, "key": key})
        return row

    def _resize(self) -> None:
        self.setColumnHidden(5, True)
        self.hide_uncertain()
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    @Slot(bool, name="toggleUncertainColumns")
    def hide_uncertain(self, hide: bool = True) -> None:
        for i in (c for c in self.dataframe.columns if c in self.UNCERTAINTY):
            self.setColumnHidden(self.dataframe.columns.get_loc(i), hide)
