# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from ..icons import icons
from .activity import ActivitiesTableWidget
from .ia import MethodsTableWidget
from brightway2 import *
from PyQt5 import QtCore, QtGui, QtWidgets


class CSList(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CSList, self).__init__(parent)
        # Runs even if selection doesn't change
        self.activated['QString'].connect(self.set_cs)
        signals.calculation_setup_selected.connect(self.sync)

    def sync(self, name):
        self.clear()
        keys = sorted(calculation_setups)
        self.insertItems(0, keys)
        self.setCurrentIndex(keys.index(name))

    def set_cs(self, name):
        signals.calculation_setup_selected.emit(name)

    @property
    def name(self):
        return self.itemText(self.currentIndex())


class CSActivityItem(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(CSActivityItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class CSAmount(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(CSAmount, self).__init__(*args)
        self.key = key


class CSActivityTableWidget(QtWidgets.QTableWidget):
    COLUMNS = {
        0: "name",
        1: "amount",
        2: "unit",
    }

    def __init__(self):
        super(CSActivityTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setSortingEnabled(True)
        self.setAcceptDrops(True)

        self.cellChanged.connect(self.filter_amount_change)
        signals.calculation_setup_selected.connect(self.sync)

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.delete_row_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Remove row", None
        )
        self.addAction(self.delete_row_action)
        self.delete_row_action.triggered.connect(self.delete_rows)

    def sync(self, name):
        self.cellChanged.disconnect(self.filter_amount_change)
        self.clear()
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(["Activity name", "Amount", "Unit"])

        for func_unit in calculation_setups[name]['inv']:
            for key, amount in func_unit.items():
                act = get_activity(key)
                new_row = self.rowCount()
                self.insertRow(new_row)
                self.setItem(new_row, 0, CSActivityItem(key, act['name']))
                self.setItem(new_row, 1, CSAmount(key, amount))
                self.setItem(new_row, 2, CSActivityItem(None, act.get('unit', 'Unknown')))

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
        if isinstance(event.source(), ActivitiesTableWidget):
            event.accept()

    def dropEvent(self, event):
        new_keys = [item.key for item in event.source().selectedItems()]
        for key in new_keys:
            act = get_activity(key)
            if act['type'] != "process":
                continue

            new_row = self.rowCount()
            self.insertRow(new_row)
            self.setItem(new_row, 0, CSActivityItem(key, act['name']))
            self.setItem(new_row, 1, CSAmount(key, "1.0"))
            self.setItem(new_row, 2, CSActivityItem(None, act.get('unit', 'Unknown')))

        event.accept()

        signals.calculation_setup_changed.emit()

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def to_python(self):
        return [{self.item(row, 0).key: self.item(row, 1).text()} for row in range(self.rowCount())]

    def filter_amount_change(self, row, col):
        if col == 1:
            signals.calculation_setup_changed.emit()


class CSMethodItem(QtWidgets.QTableWidgetItem):
    def __init__(self, method, *args):
        super(CSMethodItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.method = method


class CSMethodsTableWidget(QtWidgets.QTableWidget):
    def __init__(self):
        super(CSMethodsTableWidget, self).__init__()
        self.setColumnCount(1)
        self.setSortingEnabled(True)
        self.setAcceptDrops(True)

        signals.calculation_setup_selected.connect(self.sync)

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.delete_row_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Remove row", None
        )
        self.addAction(self.delete_row_action)
        self.delete_row_action.triggered.connect(self.delete_rows)

    def sync(self, name):
        self.clear()
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(["Name"])

        for obj in calculation_setups[name]['ia']:
            new_row = self.rowCount()
            self.insertRow(new_row)
            self.setItem(new_row, 0, CSMethodItem(obj, ", ".join(obj)))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def dragEnterEvent(self, event):
        if isinstance(event.source(), MethodsTableWidget):
            event.accept()

    def dropEvent(self, event):
        new_methods = [item.method for item in event.source().selectedItems()]
        if self.rowCount():
            existing = {self.item(index, 0).method for index in range(self.rowCount())}
        else:
            existing = {}
        for obj in new_methods:
            if obj in existing:
                continue
            new_row = self.rowCount()
            self.insertRow(new_row)
            self.setItem(new_row, 0, CSMethodItem(obj, ", ".join(obj)))
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
