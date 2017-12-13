# -*- coding: utf-8 -*-
import itertools

from brightway2 import Database
from PyQt5 import QtCore, QtGui, QtWidgets

from . table import ABTableWidget, ABStandardTable, ABTableItem
from ..style import TableStyle
from ..icons import icons
from ...signals import signals
from ...bw2extensions.commontasks import *


class ActivitiesTableNew(ABStandardTable):
    """ This is an alternative, more generic approach to filling activity tables
    as we have several ones. Not yet convinved that this approach is better than the original one.
    """
    MAX_LENGTH = 10
    HEADERS = ["Activity", "Reference product", "Location", "Unit"]

    def __init__(self, parent=None):
        super(ActivitiesTableNew, self).__init__(parent)

    def sync(self, name):
        self.database = Database(name)
        self.database.order_by = 'name'
        self.database.filters = {'type': 'process'}
        self.setHorizontalHeaderLabels(self.HEADERS)
        # self.setRowCount(min(len(self.database), self.COUNT))
        self.setRowCount(len(self.database))

        # data = get_activity_data(itertools.islice(self.database, 0, self.MAX_LENGTH))
        data = get_activity_data(itertools.islice(self.database, 0, None))
        super().update_table(data, self.HEADERS)


class ActivitiesTable(ABTableWidget):
    MAX_LENGTH = 500
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
    }
    HEADERS = ["Name", "Reference Product", "Location", "Unit"]

    def __init__(self, parent=None):
        super(ActivitiesTable, self).__init__(parent)
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))

        # Done by tab widget ``MaybeActivitiesTable`` because
        # need to ensure order to get correct row count
        # signals.database_selected.connect(self.sync)
        self.itemDoubleClicked.connect(
            lambda x: signals.open_activity_tab.emit("activities", x.key)
        )
        self.itemDoubleClicked.connect(
            lambda x: signals.add_activity_to_history.emit(x.key)
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

    @ABTableWidget.decorated_sync
    def sync(self, name, data=None):
        if not data:
            self.database = Database(name)
            self.database.order_by = 'name'
            self.database.filters = {'type': 'process'}
            data = itertools.islice(self.database, 0, self.MAX_LENGTH)
            self.setRowCount(min(len(self.database), self.MAX_LENGTH))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ABTableItem(ds.get(value, ''), key=ds.key, color=value))

        # self.setRowCount(min(len(self.database), self.MAX_LENGTH))
        # sizePolicy = QtWidgets.QSizePolicy()
        # sizePolicy.setVerticalStretch(1)
        # self.setSizePolicy(sizePolicy)

    def filter_database_changed(self, database_name):
        if not hasattr(self, "database") or self.database.name != database_name:
            return
        self.sync(self.database.name)

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.MAX_LENGTH)
        self.setRowCount(len(search_result))
        self.sync(self.database.name, search_result)
