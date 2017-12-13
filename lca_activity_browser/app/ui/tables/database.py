# -*- coding: utf-8 -*-
import arrow
from bw2data import databases
from bw2data.utils import natural_sort
from PyQt5 import QtCore

from .table import ABTableWidget, ABTableItem
from ...signals import signals


class DatabasesTable(ABTableWidget):
    HEADERS = ["Name", "Depends", "Last modified", "Size", "Read-only"]
    def __init__(self):
        super(DatabasesTable, self).__init__()
        self.setColumnCount(len(self.HEADERS))
        self.sync()
        self.connect_signals()

    def connect_signals(self):
        # SIGNAL
        self.itemDoubleClicked.connect(self.select_database)
        # SLOT
        signals.databases_changed.connect(self.sync)

    def select_database(self, item):
        signals.database_selected.emit(item.db_name)

    @ABTableWidget.decorated_sync
    def sync(self):
        self.setRowCount(len(databases))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, name in enumerate(natural_sort(databases)):
            self.setItem(row, 0, ABTableItem(name, db_name=name))
            depends = databases[name].get('depends', [])
            self.setItem(row, 1, ABTableItem("; ".join(depends), db_name=name))
            dt = databases[name].get('modified', '')
            if dt:
                dt = arrow.get(dt).humanize()
            self.setItem(row, 2, ABTableItem(dt, db_name=name))
            self.setItem(row, 3, ABTableItem(str(databases[name].get('number', [])), db_name=name))
            self.setItem(row, 4, ABTableItem(None, set_flags=[QtCore.Qt.ItemIsUserCheckable]))

