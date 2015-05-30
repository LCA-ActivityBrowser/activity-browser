# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from bw2data import databases
from bw2data.utils import natural_sort
from PyQt4 import QtCore, QtGui
import arrow
import itertools


class DatabasesTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Depends", "Modified"])
        self.sync()

    def sync(self):
        self.setRowCount(len(databases))
        for row, name in enumerate(natural_sort(databases)):
            self.setItem(row, 0, QtGui.QTableWidgetItem(name))
            depends = databases[name].get('depends', [])
            self.setItem(row, 1, QtGui.QTableWidgetItem("; ".join(depends)))
            dt = databases[name].get('modified', '')
            if dt:
                dt = arrow.get(dt).humanize()
            self.setItem(row, 2, QtGui.QTableWidgetItem(dt))

        # self.resizeColumnsToContents()
        # self.resizeRowsToContents()
        # http://stackoverflow.com/questions/8947977/how-do-i-get-rid-of-this-whitespace-in-my-qtablewidget


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
            for col, key in self.COLUMNS.items():
                self.setItem(row, col, QtGui.QTableWidgetItem(ds.get(key, '')))
