# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore


class TableModel(QtCore.QAbstractTableModel):
    """Base class to avoid repetition"""
    # API docs: http://pyqt.sourceforge.net/Docs/PyQt4/qabstracttablemodel.html

    HEADER_LABELS = {
        0: "Name"
    }

    def columnCount(self, *args):
        return len(self.HEADER_LABELS)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.HEADER_LABELS[section]
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)
