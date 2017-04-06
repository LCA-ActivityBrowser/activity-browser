# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from brightway2 import *
from PyQt4 import QtCore, QtGui


class Item(QtGui.QTableWidgetItem):
    def __init__(self, key, *args):
        super(Item, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class ActivitiesHistoryWidget(QtGui.QTableWidget):
    COUNT = 40
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
    }

    def __init__(self, *args):
        super(ActivitiesHistoryWidget, self).__init__(*args)
        self.setDragEnabled(True)
        self.setColumnCount(4)
        self.setRowCount(0)
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])

        self.itemDoubleClicked.connect(
            lambda x: signals.activity_selected.emit(x.key)
        )

        signals.activity_selected.connect(self.add_activity)
        signals.project_selected.connect(self.clear_history)

    def add_activity(self, key):
        for row in range(self.rowCount()):
            if self.item(row, 0).key == key:
                self.removeRow(row)

        ds = get_activity(key)
        self.insertRow(0)
        for col, value in self.COLUMNS.items():
            self.setItem(0, col, Item(key, ds.get(value, '')))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def clear_history(self):
        self.clear()
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])
        self.setRowCount(0)
