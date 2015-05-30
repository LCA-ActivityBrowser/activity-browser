# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from bw2data import databases
from PyQt4 import QtCore, QtGui
import arrow


class DatabasesTableWidget(QtGui.QTableWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Name", "Depends", "Modified"])
        self.sync()

    def sync(self):
        self.setRowCount(len(databases))
        for row, name in enumerate(sorted(databases)):
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
