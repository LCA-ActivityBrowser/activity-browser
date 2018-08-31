# -*- coding: utf-8 -*-
from bw2data import projects
from PyQt5 import QtCore, QtWidgets

from .table import ABTableWidget, ABTableItem
from ...signals import signals


class ProjectListWidget(QtWidgets.QComboBox):
    def __init__(self):
        super(ProjectListWidget, self).__init__()
        self.connect_signals()
        self.project_names = None

    def connect_signals(self):
        self.activated.connect(self.on_activated)
        signals.project_selected.connect(self.sync)
        signals.projects_changed.connect(self.sync)

    def sync(self):
        self.clear()
        self.project_names = sorted([project.name for project in projects])
        self.addItems(self.project_names)
        index = self.project_names.index(projects.current)
        self.setCurrentIndex(index)

    def on_activated(self, index):
        signals.change_project.emit(self.project_names[index])


class ProjectTable(ABTableWidget):
    """ Table displaying projects. Unused at this moment. """
    HEADERS = ["Name"]
    def __init__(self):
        super(ProjectTable, self).__init__()
        self.setColumnCount(len(self.HEADERS))
        self.connect_signals()
        self.sync()

    def connect_signals(self):
        pass

    def select_database(self, item):
        pass

    @ABTableWidget.decorated_sync
    def sync(self):
        self.setRowCount(len(projects))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, project in enumerate(projects):
            self.setItem(row, 0, ABTableItem(project.name, project=project.name))
