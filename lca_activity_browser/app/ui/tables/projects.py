# -*- coding: utf-8 -*-
from bw2data import projects
from PyQt5 import QtCore, QtWidgets


class ProjectListModel(QtCore.QAbstractListModel):
    def rowCount(self, *args):
        return len(projects)

    def data(self, index, *args):
        row = index.row()
        names = sorted([project.name for project in projects])
        return names[row]


class ProjectListWidget(QtWidgets.QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self._model = ProjectListModel()
        self.setModel(self._model)
        default_index = sorted([project.name for project in projects]).index("default")
        self.setCurrentIndex(default_index)
