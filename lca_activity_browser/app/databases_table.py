# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .models import TableModel
from bw2data import databases
from PyQt4 import QtCore, QtGui


class DatabasesTableModel(TableModel):
    """Table that lists databases.

    Columns are:
        0: Name

    """
    # API docs: http://pyqt.sourceforge.net/Docs/PyQt4/qabstracttablemodel.html

    # Use .revert() to sync with underlying data
    # Adding/deleting done through controller (?)
    COLUMN_MAPPING = {
        0: 'name',
    }

    def rowCount(self, *args):
        return len(databases)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            row, column = index.row(), index.column()
            sorted_keys = sorted(databases.keys())
            if column == 0:
                return sorted_keys[row]
            else:
                return databases[sorted_keys[row]][self.COLUMN_MAPPING[column]]
        else:
            return QtCore.QVariant


class DatabasesTableView(QtGui.QTableView):
    pass


class DatabasesTableWidget(QtGui.QWidget):
    def __init__(self):
        super(DatabasesTableWidget, self).__init__()
        self.model = DatabasesTableModel(self)
        self.view = DatabasesTableView(self)
        self.view.setModel(self.model)
        self.view.setColumnWidth(0, 250)

    def reset(self):
        self.model.layoutAboutToBeChanged.emit()
        self.model.beginResetModel()
        self.model.endResetModel()
        # self.model.reset()
        # self.model.revert()
        self.model.layoutChanged.emit()
        self.view.resizeRowsToContents()
        # self.view.adjustSize()

