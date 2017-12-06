# -*- coding: utf-8 -*-
from ...signals import signals
from ..icons import icons
from . table import ActivityBrowserTableWidget
import brightway2 as bw
from PyQt5 import QtCore, QtGui, QtWidgets


class Item(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(Item, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class ActivitiesHistoryWidget(ActivityBrowserTableWidget):
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
            lambda x: signals.open_activity_tab.emit("activities", self.currentItem().key)
        )
        self.itemDoubleClicked.connect(
            lambda x: signals.activity_selected.emit(x.key)
        )
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.open_left_tab_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open in new tab", None
        )
        self.addAction(self.open_left_tab_action)
        self.open_left_tab_action.triggered.connect(
            lambda x: signals.open_activity_tab.emit(
                "activities", self.currentItem().key
            )
        )

        signals.activity_selected.connect(self.add_activity)
        signals.project_selected.connect(self.clear_history)

    def add_activity(self, key):
        for row in range(self.rowCount()):
            if self.item(row, 0).key == key:
                self.removeRow(row)
                break  # otherwise iterating over object that has changed

        ds = bw.get_activity(key)
        self.insertRow(0)
        for col, value in self.COLUMNS.items():
            self.setItem(0, col, Item(key, ds.get(value, '')))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def clear_history(self):
        self.clear()
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])
        self.setRowCount(0)
