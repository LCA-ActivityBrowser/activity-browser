# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

from activity_browser.app.bwutils.commontasks import bw_keys_to_AB_names

from .delegates import FloatDelegate, ViewOnlyDelegate
from .inventory import ActivitiesBiosphereTable
from .table import ABTableWidget, ABTableItem
from .impact_categories import MethodsTable
from .views import ABDataFrameEdit, dataframe_sync
from ..icons import icons, qicons
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


class CSActivityTable(ABTableWidget):
    COLUMNS = {
        0: "amount",
        1: "unit",
        2: "reference product",
        3: "name",
        4: "location",
        5: "database",
    }
    HEADERS = ["Amount", "Unit", "Product", "Activity", "Location", "Database"]

    def __init__(self):
        super(CSActivityTable, self).__init__()
        self.setColumnCount(len(self.HEADERS))
        self.setAcceptDrops(True)
        self.setup_context_menu()
        self.connect_signals()

    def setup_context_menu(self):
        self.delete_row_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Remove row", None
        )
        self.addAction(self.delete_row_action)
        self.delete_row_action.triggered.connect(self.delete_rows)

    def connect_signals(self):
        """ Connect signals to slots. """
        self.cellChanged.connect(self.filter_amount_change)
        signals.calculation_setup_selected.connect(self.sync)

    def append_row(self, key, amount='1.0'):
        try:
            act = bw.get_activity(key)
            new_row = self.rowCount()
            self.insertRow(new_row)
            self.setItem(new_row, 0, ABTableItem(
                amount, key=key, set_flags=[QtCore.Qt.ItemIsEditable], color="amount")
            )
            self.setItem(new_row, 1, ABTableItem(act.get('unit'), key=key, color="unit"))
            self.setItem(new_row, 2, ABTableItem(act.get('reference product'),
                                                 key=key, color="product"))
            self.setItem(new_row, 3, ABTableItem(act.get('name'), key=key, color="name"))
            self.setItem(new_row, 4, ABTableItem(str(act.get('location')), key=key, color="location"))
            self.setItem(new_row, 5, ABTableItem(act.get('database'), key=key, color="database"))
        except:
            print("Could not load key in Calculation Setup: ", key)

    def sync(self, name):
        self.current_cs = name
        self.cellChanged.disconnect(self.filter_amount_change)
        self.clear()
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(self.HEADERS)

        for func_unit in bw.calculation_setups[name]['inv']:
            for key, amount in func_unit.items():
                self.append_row(key, str(amount))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.cellChanged.connect(self.filter_amount_change)

    def delete_rows(self, *args):
        to_delete = []
        for range_obj in self.selectedRanges():
            bottom = range_obj.bottomRow()
            top = range_obj.topRow()
            to_delete.extend(list(range(top, bottom + 1)))
        to_delete.sort(reverse=True)
        for row in to_delete:
            self.removeRow(row)
        signals.calculation_setup_changed.emit()

    def dragEnterEvent(self, event):
        if isinstance(event.source(), ActivitiesBiosphereTable):
            event.accept()

    def dropEvent(self, event):
        # new_keys = [item.key for item in event.source().selectedItems()]
        source_table = event.source()
        print('Dropevent from:', source_table)
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        event.accept()

        for key in keys:
            act = bw.get_activity(key)
            if act.get('type', 'process') != "process":
                continue
            self.append_row(key)

        signals.calculation_setup_changed.emit()

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def to_python(self):
        return [{self.item(row, 0).key: float(self.item(row, 0).text())} for
                row in range(self.rowCount())]

    def filter_amount_change(self, row, col):
        if col == 0:
            try:
                float(self.item(row, col).text())
                signals.calculation_setup_changed.emit()
            except ValueError as e:
                self.sync(self.current_cs)


class CSMethodsTable(ABTableWidget):
    HEADERS = ["Name", "Unit", "# CFs"]

    def __init__(self):
        super(CSMethodsTable, self).__init__()
        self.setColumnCount(len(self.HEADERS))
        self.setAcceptDrops(True)
        self.setup_context_menu()
        self.connect_signals()

    def setup_context_menu(self):
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.delete_row_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Remove row", None
        )
        self.addAction(self.delete_row_action)
        self.delete_row_action.triggered.connect(self.delete_rows)

    def connect_signals(self):
        signals.calculation_setup_selected.connect(self.sync)

    def append_row(self, method):
        new_row = self.rowCount()
        self.insertRow(new_row)
        method_metadata = bw.methods[method]
        self.setItem(new_row, 0, ABTableItem(', '.join(method), method=method))
        self.setItem(new_row, 1, ABTableItem(method_metadata.get('unit', "Unknown"), method=method))
        num_cfs = method_metadata.get('num_cfs', 0)
        self.setItem(new_row, 2, ABTableItem(str(num_cfs), method=method, number=num_cfs))

    def sync(self, name):
        self.clear()
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(self.HEADERS)

        for method in bw.calculation_setups[name]['ia']:
            self.append_row(method)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def dragEnterEvent(self, event):
        if isinstance(event.source(), MethodsTable):
            event.accept()

    def dropEvent(self, event):
        new_methods = [item.method for item in event.source().selectedItems()]
        if self.rowCount():
            existing = {self.item(index, 0).method for index in range(self.rowCount())}
        else:
            existing = {}
        for method in new_methods:
            if method in existing:
                continue
            self.append_row(method)
        event.accept()

        signals.calculation_setup_changed.emit()

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def delete_rows(self, *args):
        to_delete = []
        for range_obj in self.selectedRanges():
            bottom = range_obj.bottomRow()
            top = range_obj.topRow()
            to_delete.extend(list(range(top, bottom + 1)))
        to_delete.sort(reverse=True)
        for row in to_delete:
            self.removeRow(row)
        signals.calculation_setup_changed.emit()

    def to_python(self):
        return [self.item(row, 0).method for row in range(self.rowCount())]
