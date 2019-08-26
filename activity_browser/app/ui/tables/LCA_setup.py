# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PyQt5 import QtWidgets

from activity_browser.app.bwutils.commontasks import bw_keys_to_AB_names

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
        self.clear()
        keys = sorted(bw.calculation_setups)
        self.insertItems(0, keys)
        self.setCurrentIndex(keys.index(name))

    def set_cs(self, name):
        signals.calculation_setup_selected.emit(name)

    @property
    def name(self):
        return self.itemText(self.currentIndex())


class CSActivityTable(ABDataFrameEdit):
    FIELDS = [
        "amount", "unit", "reference product", "name", "location", "database",
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
                bw_keys_to_AB_names[field]: act.get(field)
                for field in self.FIELDS
            }
            row.update({"Amount": amount, "key": key})
            return row
        except TypeError:
            print("Could not load key in Calculation Setup: ", key)

    @dataframe_sync
    def sync(self, name: str = None):
        if self.current_cs is None and name is None:
            raise ValueError("'name' cannot be None if no name is set")
        if name:
            self.current_cs = name
        data = [
            self.build_row(key, amount)
            for func_unit in bw.calculation_setups[self.current_cs]['inv']
            for key, amount in func_unit.items()
        ]
        colnames = [bw_keys_to_AB_names[x] for x in self.FIELDS] + ["key"]
        self.dataframe = pd.DataFrame(data, columns=colnames)

    def delete_rows(self):
        indices = [self.get_source_index(p) for p in self.selectedIndexes()]
        rows = [i.row() for i in indices]
        self.dataframe.drop(rows, axis=0, inplace=True)
        signals.calculation_setup_changed.emit()
        self.sync()

    def to_python(self) -> list:
        data = self.dataframe[["Amount", "key"]].to_dict(orient="records")
        return [{x["key"]: x["Amount"]} for x in data]

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.popup(a0.globalPos())
        menu.exec()

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        """ If data in the model is changed, update the dataframe to match.
        """
        if topLeft == bottomRight:
            index = self.get_source_index(topLeft)
            self.dataframe.iat[index.row(), index.column()] = float(topLeft.data())
        signals.calculation_setup_changed.emit()

    def dragEnterEvent(self, event):
        source = event.source()
        if hasattr(source, "technosphere") and source.technosphere:
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        event.accept()
        source_table = event.source()
        print('Dropevent from:', source_table)
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        data = [self.build_row(key) for key in keys]
        self.dataframe = self.dataframe.append(data, ignore_index=True)
        signals.calculation_setup_changed.emit()
        self.sync()


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
        data = [
            self.build_row(method)
            for method in bw.calculation_setups[self.current_cs]["ia"]
        ]
        self.dataframe = pd.DataFrame(data, columns=self.HEADERS)

    def delete_rows(self):
        indices = [self.get_source_index(p) for p in self.selectedIndexes()]
        rows = [i.row() for i in indices]
        self.dataframe.drop(rows, axis=0, inplace=True)
        signals.calculation_setup_changed.emit()
        self.sync()

    def to_python(self):
        data = self.dataframe[["method"]].to_dict(orient="list")
        return data["method"]

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.delete, "Remove row", self.delete_rows)
        menu.popup(a0.globalPos())
        menu.exec()

    def dragEnterEvent(self, event):
        if isinstance(event.source(), MethodsTable):
            event.accept()

    def dragMoveEvent(self, event) -> None:
        pass

    def dropEvent(self, event):
        new_methods = [row["method"] for row in event.source().selectedItems()]
        old_methods = set(m for m in self.dataframe["method"])
        data = [self.build_row(m) for m in new_methods if m not in old_methods]
        if data:
            self.dataframe = self.dataframe.append(data, ignore_index=True)
            signals.calculation_setup_changed.emit()
            self.sync()
        event.accept()
