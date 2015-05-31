# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from brightway2 import Database
from PyQt4 import QtCore, QtGui
import itertools


class ActivityItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, key=None):
        super(ActivityItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class ActivitiesTableWidget(QtGui.QTableWidget):
    COUNT = 100
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
    }

    def __init__(self):
        super(ActivitiesTableWidget, self).__init__()
        self.setVisible(False)
        self.setDragEnabled(True)
        self.setColumnCount(4)

        signals.database_selected.connect(self.sync)

    def sync(self, name):
        self.clear()
        self.setRowCount(self.COUNT)
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])
        database = Database(name)
        database.order_by = 'name'
        database.filters = {'type': 'process'}
        data = itertools.islice(database, 0, self.COUNT)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.get(value, ''), key=ds.key))
