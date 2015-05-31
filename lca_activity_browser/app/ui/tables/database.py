# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from bw2data import databases
from bw2data.utils import natural_sort
from PyQt4 import QtCore, QtGui
import arrow


class DatabaseItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, db_name=None):
        super(DatabaseItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.db_name = db_name


class DatabasesTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.setColumnCount(3)
        self.sync()

        self.itemDoubleClicked.connect(self.select_database)

    def sync(self):
        self.clear()
        self.setRowCount(len(databases))
        self.setHorizontalHeaderLabels(["Name", "Depends", "Last modified"])
        for row, name in enumerate(natural_sort(databases)):
            self.setItem(row, 0, DatabaseItem(name, db_name=name))
            depends = databases[name].get('depends', [])
            self.setItem(row, 1, DatabaseItem("; ".join(depends), db_name=name))
            dt = databases[name].get('modified', '')
            if dt:
                dt = arrow.get(dt).humanize()
            self.setItem(row, 2, DatabaseItem(dt, db_name=name))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def select_database(self, item):
        signals.database_selected.emit(item.db_name)
