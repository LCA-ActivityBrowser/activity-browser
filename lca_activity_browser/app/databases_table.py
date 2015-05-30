# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from bw2data import databases
from bw2data.utils import natural_sort
from PyQt4 import QtCore, QtGui
import arrow
import itertools


class DatabaseItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, db_name=None):
        super(DatabaseItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.db_name = db_name


class DatabasesTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Depends", "Modified"])
        self.sync()

    def sync(self):
        self.setRowCount(len(databases))
        for row, name in enumerate(natural_sort(databases)):
            self.setItem(row, 0, DatabaseItem(name, db_name=name))
            depends = databases[name].get('depends', [])
            self.setItem(row, 1, DatabaseItem("; ".join(depends), db_name=name))
            dt = databases[name].get('modified', '')
            if dt:
                dt = arrow.get(dt).humanize()
            self.setItem(row, 2, DatabaseItem(dt, db_name=name))

        # self.resizeColumnsToContents()
        # self.resizeRowsToContents()
        # http://stackoverflow.com/questions/8947977/how-do-i-get-rid-of-this-whitespace-in-my-qtablewidget


class ActivityItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, key=None):
        super(ActivityItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class ActivitiesTableWidget(QtGui.QTableWidget):
    COUNT = 40
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit"
    }

    def __init__(self):
        super(ActivitiesTableWidget, self).__init__()
        self.setVisible(False)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Reference Product", "Location", "Unit"])

    def sync(self, database):
        self.setRowCount(self.COUNT)
        data = itertools.islice(database, 0, self.COUNT)
        for row, ds in enumerate(data):
            for col, value in self.COLUMNS.items():
                self.setItem(row, col, ActivityItem(ds.get(value, ''), key=ds.key))
