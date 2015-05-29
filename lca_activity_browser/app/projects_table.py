# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .models import TableModel
from bw2data import projects
from PyQt4 import QtCore, QtGui


class ProjectsTableModel(TableModel):
    """Table that lists projects.

    Columns are:
        0: Name

    """
    # API docs: http://pyqt.sourceforge.net/Docs/PyQt4/qabstracttablemodel.html

    # Use .revert() to sync with underlying data
    # Adding/deleting done through controller (?)

    def rowCount(self, *args):
        return len(projects)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            row, column = index.row(), index.column()
            names = sorted([project.name for project in projects])
            return names[row]
        else:
            return QtCore.QVariant


class ProjectsTableView(QtGui.QTableView):
    pass


class ProjectsTableWidget(QtGui.QWidget):
    def __init__(self):
        super(ProjectsTableWidget, self).__init__()
        self.model = ProjectsTableModel(self)
        self.view = ProjectsTableView(self)
        self.view.setModel(self.model)
        self.view.setColumnWidth(0, 250)
