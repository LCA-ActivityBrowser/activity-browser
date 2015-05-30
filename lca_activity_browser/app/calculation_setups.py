# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from PyQt4 import QtCore, QtGui


class CSItem(QtGui.QTableWidgetItem):
    def __init__(self, *args, key=None):
        super(CSItem, self).__init__(*args)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.key = key


class CSActivityTableWidget(QtGui.QTableWidget):
    COLUMNS = {
        0: "name",
        1: "amount",
        2: "unit",
    }

    def __init__(self):
        super(CSActivityTableWidget, self).__init__()
        self.setColumnCount(3)
        self.setSortingEnabled(True)
        self.setAcceptDrops(True)
        self.setHorizontalHeaderLabels(["Activity name", "Amount", "Unit"])

    def dropEvent(self, event):
        new_keys = [item.key for item in event.source().selectedItems()]
        for key in new_keys:
            act = get_activity(key)
            if act['type'] != "process":
                continue

            new_row = self.rowCount()
            self.insertRow(new_row)
            self.setItem(new_row, 0, CSItem(act['name'], key=key))
            self.setItem(new_row, 1, CSItem("1.0", key=key))
            self.setItem(new_row, 2, CSItem(act.get('unit', 'Unknown')))

        event.accept()
