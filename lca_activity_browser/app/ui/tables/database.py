# -*- coding: utf-8 -*-
import arrow
from bw2data import databases
from bw2data.utils import natural_sort
from PyQt5 import QtCore, QtWidgets

from .table import ABTableWidget
from ...signals import signals


class DatabaseItem(QtWidgets.QTableWidgetItem):
    def __init__(self, db_name, *args):
        super(DatabaseItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.db_name = db_name


class DatabasesTable(ABTableWidget):
    def __init__(self):
        super(DatabasesTable, self).__init__()
        self.setColumnCount(3)
        self.sync()

        self.itemDoubleClicked.connect(self.select_database)
        signals.databases_changed.connect(self.sync)

    def sync(self):
        super().sync()
        self.setRowCount(len(databases))
        self.setHorizontalHeaderLabels(["Name", "Depends", "Last modified"])
        for row, name in enumerate(natural_sort(databases)):
            self.setItem(row, 0, DatabaseItem(name, name))
            depends = databases[name].get('depends', [])
            self.setItem(row, 1, DatabaseItem(name, "; ".join(depends)))
            dt = databases[name].get('modified', '')
            if dt:
                dt = arrow.get(dt).humanize()
            self.setItem(row, 2, DatabaseItem(name, dt))

        super().resize_custom()

    def select_database(self, item):
        signals.database_selected.emit(item.db_name)
