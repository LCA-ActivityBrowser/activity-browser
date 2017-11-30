# -*- coding: utf-8 -*-
from ...signals import signals
from bw2data import databases
from bw2data.utils import natural_sort
from PyQt5 import QtCore, QtWidgets
import arrow


class DatabaseItem(QtWidgets.QTableWidgetItem):
    def __init__(self, db_name, *args):
        super(DatabaseItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.db_name = db_name


class DatabasesTableWidget(QtWidgets.QTableWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.setColumnCount(3)
        self.sync()

        self.itemDoubleClicked.connect(self.select_database)
        signals.databases_changed.connect(self.sync)

    def sync(self):
        self.clear()
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

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def select_database(self, item):
        signals.database_selected.emit(item.db_name)
