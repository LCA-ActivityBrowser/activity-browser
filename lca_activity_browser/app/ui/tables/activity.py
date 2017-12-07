# -*- coding: utf-8 -*-
from ...signals import signals
from ..icons import icons
from . table import ABTableWidget
from brightway2 import Database
from PyQt5 import QtCore, QtGui, QtWidgets
import itertools


class ActivityItem(QtWidgets.QTableWidgetItem):
    def __init__(self, key, *args):
        super(ActivityItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class ActivitiesTable(ABTableWidget):
    COUNT = 500
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
    }

    def __init__(self, parent=None):
        super(ActivitiesTable, self).__init__(parent)
        self.setDragEnabled(True)
        self.setColumnCount(4)

        # Done by tab widget ``MaybeActivitiesTable`` because
        # need to ensure order to get correct row count
        # signals.database_selected.connect(self.sync)
        self.itemDoubleClicked.connect(
            lambda x: signals.open_activity_tab.emit("activities", x.key)
        )
        self.itemDoubleClicked.connect(
            lambda x: signals.activity_selected.emit(x.key)
        )

        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.add_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.copy_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.copy), "Copy activity", None
        )
        self.delete_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete activity", None
        )
        self.open_left_tab_action = QtWidgets.QAction(
            QtGui.QIcon(icons.left), "Open in new tab", None
        )
        self.addAction(self.add_activity_action)
        self.addAction(self.copy_activity_action)
        self.addAction(self.delete_activity_action)
        self.addAction(self.open_left_tab_action)
        self.add_activity_action.triggered.connect(
            lambda: signals.new_activity.emit(self.database.name))
        self.copy_activity_action.triggered.connect(
            lambda x: signals.copy_activity.emit(self.currentItem().key)
        )
        self.delete_activity_action.triggered.connect(
            lambda x: signals.delete_activity.emit(self.currentItem().key)
        )
        self.open_left_tab_action.triggered.connect(
            lambda x: signals.open_activity_tab.emit(
                "activities", self.currentItem().key
            )
        )
        signals.database_changed.connect(self.filter_database_changed)

    def sync(self, name):
        super().sync()
        self.database = Database(name)
        self.database.order_by = 'name'
        self.database.filters = {'type': 'process'}
        self.setRowCount(min(len(self.database), self.COUNT))
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])
        data = itertools.islice(self.database, 0, self.COUNT)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.key, ds.get(value, '')))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # sizePolicy = QtWidgets.QSizePolicy()
        # sizePolicy.setVerticalStretch(1)
        # self.setSizePolicy(sizePolicy)
        # self.setMaximumHeight(
        #     # btable.horizontalHeader().height()
        #     + 5*self.rowHeight(0)
        #     + self.autoScrollMargin()
        # )

    def filter_database_changed(self, database_name):
        if not hasattr(self, "database") or self.database.name != database_name:
            return
        self.sync(self.database.name)

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        self.clear()
        search_result = self.database.search(search_term, limit=self.COUNT)
        self.setRowCount(len(search_result))
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])
        for row, ds in enumerate(search_result):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.key, ds.get(value, '')))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
