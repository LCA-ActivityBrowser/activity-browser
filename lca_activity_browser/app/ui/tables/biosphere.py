# -*- coding: utf-8 -*-
import itertools

import brightway2 as bw

from . table import ABTableWidget
from .activity import ActivityItem
from ...signals import signals


class BiosphereFlowsTable(ABTableWidget):
    COUNT = 100
    COLUMNS = {
        0: "name",
        2: "unit"
    }

    def __init__(self):
        super(BiosphereFlowsTable, self).__init__()
        self.setColumnCount(3)
        self.setDragEnabled(True)
        self.setHorizontalHeaderLabels(["Name", "Categories", "Unit"])

        signals.database_selected.connect(self.sync)

    def sync(self, name):
        self.clear()
        self.database = bw.Database(name)
        self.database.order_by = 'name'
        self.database.filters = {'type': 'emission'}
        self.setRowCount(min(len(self.database), self.COUNT))
        self.setHorizontalHeaderLabels(["Name", "Categories", "Unit"])
        data = itertools.islice(self.database, 0, self.COUNT)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.key, ds.get(value, '')))
            self.setItem(row, 1, ActivityItem(ds.key, ", ".join(ds.get('categories', []))))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        # sizePolicy = QtWidgets.QSizePolicy()
        # sizePolicy.setVerticalStretch(20)
        # self.setSizePolicy(sizePolicy)

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.COUNT, **self.database.filters)
        self.clear()
        self.setRowCount(len(search_result))
        self.setHorizontalHeaderLabels(["Name", "Categories", "Unit"])
        for row, ds in enumerate(search_result):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.key, ds.get(value, '')))
            self.setItem(row, 1, ActivityItem(ds.key, ", ".join(ds.get('categories', []))))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
