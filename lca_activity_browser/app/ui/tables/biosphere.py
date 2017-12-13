# -*- coding: utf-8 -*-
import itertools

import brightway2 as bw

from . table import ABTableWidget, ABTableItem
from ...signals import signals


class BiosphereFlowsTable(ABTableWidget):
    MAX_LENGTH = 100
    COLUMNS = {
        0: "name",
        2: "unit"
    }
    HEADERS = ["Name", "Categories", "Unit"]

    def __init__(self):
        super(BiosphereFlowsTable, self).__init__()
        self.setDragEnabled(True)
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)

        signals.database_selected.connect(self.sync)

    @ABTableWidget.decorated_sync
    def sync(self, name, data=None):
        self.setHorizontalHeaderLabels(self.HEADERS)
        if not data:
            self.database = bw.Database(name)
            self.database.order_by = 'name'
            self.database.filters = {'type': 'emission'}
            self.setRowCount(min(len(self.database), self.MAX_LENGTH))
            data = itertools.islice(self.database, 0, self.MAX_LENGTH)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ABTableItem(ds.get(value, ''), key=ds.key, color=value))
            self.setItem(row, 1, ABTableItem(", ".join(ds.get('categories', [])), key=ds.key))

        # sizePolicy = QtWidgets.QSizePolicy()
        # sizePolicy.setVerticalStretch(20)
        # self.setSizePolicy(sizePolicy)

    def reset_search(self):
        self.sync(self.database.name)

    def search(self, search_term):
        search_result = self.database.search(search_term, limit=self.MAX_LENGTH)
        self.setRowCount(len(search_result))
        self.sync(self.database.name, search_result)
