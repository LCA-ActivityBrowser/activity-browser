# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.backends.peewee import ActivityDataset
import pandas as pd
from PySide2 import QtWidgets

from activity_browser.app.bwutils.commontasks import AB_names_to_bw_keys

from .delegates import FloatDelegate, ViewOnlyDelegate
from .impact_categories import MethodsTable
from .views import ABDataFrameEdit, ABDataFrameView, dataframe_sync
from ..icons import qicons
from ...signals import signals


class CSList(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CSList, self).__init__(parent)
        # Runs even if selection doesn't change
        self.activated['QString'].connect(self.set_cs)
        signals.calculation_setup_selected.connect(self.sync)

    def sync(self, name):
        self.blockSignals(True)
        self.clear()
        keys = sorted(bw.calculation_setups)
        self.insertItems(0, keys)
        self.blockSignals(False)
        self.setCurrentIndex(keys.index(name))

    @staticmethod
    def set_cs(name: str):
        signals.calculation_setup_selected.emit(name)

    @property
    def name(self) -> str:
        return self.currentText()


class CSActivityTable(ABDataFrameEdit):
    HEADERS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))

        self.current_cs = None
        self._connect_signals()

    def _connect_signals(self):
        signals.calculation_setup_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)

    def _resize(self):
        self.setColumnHidden(6, True)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def build_row(self, key: tuple, amount: float=1.0) -> dict:
        try:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                raise TypeError("Activity is not of type 'process'")
            row = {
                key: act.get(AB_names_to_bw_keys[key], "")
                for key in self.HEADERS
            }
            row.update({"Amount": amount, "key": key})
            return row
        except (TypeError, ActivityDataset.DoesNotExist):
            print("Could not load key in Calculation Setup: ", key)
            return {}

    @dataframe_sync
    def sync(self, name: str = None):
        if self.current_cs is None and name is None:
            raise ValueError("'name' cannot be None if no name is set")
        if name:
            self.current_cs = name
        setup = bw.calculation_setups.get(self.current_cs, {})
        data = [
            self.build_row(key, amount) for func_unit in setup.get('inv', [])
            for key, amount in func_unit.items()
        ]
        self.dataframe = pd.DataFrame(data, columns=self.HEADERS + ["key"])
        # Drop rows where the fu key was invalid in some way.
        self.dataframe = self.dataframe.dropna()

    def get_key(self, proxy) -> tuple:
        index = self.get_source_index(proxy)
        return self.dataframe.iat[index.row(), self.dataframe.columns.get_loc("key")]

    def delete_rows(self):
        keys = set(self.get_key(p) for p in self.selectedIndexes())
        # If the fu contains no keys to be removed, add it to the new list
        new_fu_list = [
            fu for fu in bw.calculation_setups[self.current_cs]['inv']
            if keys.isdisjoint(fu)
        ]
        bw.calculation_setups[self.current_cs]["inv"] = new_fu_list
        self.sync()
        signals.calculation_setup_changed.emit()

    def to_python(self) -> list:
        data = self.dataframe[["Amount", "key"]].to_dict(orient="records")
        return [{x["key"]: x["Amount"]} for x in data]

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.exec_(a0.globalPos())

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        """ If data in the model is changed, update the dataframe to match.
        """
        if topLeft == bottomRight:
            index = self.get_source_index(topLeft)
            self.dataframe.iat[index.row(), index.column()] = float(topLeft.data())
        signals.calculation_setup_changed.emit()

    def dragEnterEvent(self, event):
        if getattr(event.source(), "technosphere", False):
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        event.accept()
        source = event.source()
        print('Dropevent from:', source)
        data = ({source.get_key(p): 1.0} for p in source.selectedIndexes())
        existing = set(self.dataframe["key"])
        for fu in data:
            if existing.isdisjoint(fu):
                bw.calculation_setups[self.current_cs]["inv"].append(fu)
        self.sync()
        signals.calculation_setup_changed.emit()


class CSMethodsTable(ABDataFrameView):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.current_cs = None
        self._connect_signals()

    def _connect_signals(self):
        signals.calculation_setup_selected.connect(self.sync)

    def _resize(self):
        self.setColumnHidden(3, True)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def build_row(self, method: tuple) -> dict:
        method_metadata = bw.methods[method]
        return {
            "Name": ', '.join(method),
            "Unit": method_metadata.get('unit', "Unknown"),
            "# CFs": method_metadata.get('num_cfs', 0),
            "method": method,
        }

    @dataframe_sync
    def sync(self, name: str = None):
        if name:
            self.current_cs = name
            self.dataframe = pd.DataFrame([
                self.build_row(method)
                for method in bw.calculation_setups[self.current_cs]["ia"]
            ], columns=self.HEADERS)

    def delete_rows(self):
        indices = [self.get_source_index(p) for p in self.selectedIndexes()]
        rows = [i.row() for i in indices]
        self.dataframe.drop(rows, axis=0, inplace=True)
        self.sync()
        signals.calculation_setup_changed.emit()

    def to_python(self):
        return self.dataframe["method"].to_list()

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        if isinstance(event.source(), MethodsTable):
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        event.accept()
        new_methods = [row["method"] for row in event.source().selectedItems()]
        old_methods = set(m for m in self.dataframe["method"])
        data = [self.build_row(m) for m in new_methods if m not in old_methods]
        if data:
            self.dataframe = self.dataframe.append(data, ignore_index=True)
            self.sync()
            signals.calculation_setup_changed.emit()
