# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtGui, QtWidgets

from .inventory import ActivitiesTable
from .table import ABTableWidget, ABTableItem
from .impact_categories import MethodsTable
from ..icons import icons
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
            self.setItem(new_row, 4, ABTableItem(act.get('location'), key=key, color="location"))
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
        if isinstance(event.source(), ActivitiesTable):
            event.accept()

    def dropEvent(self, event):
        new_keys = [item.key for item in event.source().selectedItems()]
        for key in new_keys:
            act = bw.get_activity(key)
            if act.get('type', 'process') != "process":
                continue
            self.append_row(key)

        event.accept()

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
