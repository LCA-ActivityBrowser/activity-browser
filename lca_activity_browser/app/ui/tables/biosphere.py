# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from .activity import ActivityItem
from brightway2 import databases, Database
from bw2data.utils import natural_sort
from PyQt4 import QtCore, QtGui
import itertools


class FlowsTableWidget(QtGui.QTableWidget):
    COUNT = 100
    COLUMNS = {
        0: "name",
        2: "unit"
    }

    def __init__(self):
        super(FlowsTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Categories", "Unit"])

        signals.database_selected.connect(self.sync)

    def sync(self, name):
        self.clear()
        self.setRowCount(self.COUNT)
        self.setHorizontalHeaderLabels(["Name", "Categories", "Unit"])
        database = Database(name)
        database.order_by = 'name'
        database.filters = {'type': 'emission'}
        data = itertools.islice(database, 0, self.COUNT)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.get(value, ''), key=ds.key))
            self.setItem(row, 1, ActivityItem(", ".join(ds.get('categories', [])), key=ds.key))
