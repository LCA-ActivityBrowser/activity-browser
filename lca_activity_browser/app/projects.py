# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui
from bw2data import projects


class ProjectListModel(QtCore.QAbstractListModel):
    def rowCount(self, *args):
        return len(projects)

    def data(self, index, *args):
        row = index.row()
        names = sorted([project.name for project in projects])
        return names[row]


class ProjectListWidget(QtGui.QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.setModel(ProjectListModel())
        default_index = sorted([project.name for project in projects]).index("default")
        self.setCurrentIndex(default_index)
