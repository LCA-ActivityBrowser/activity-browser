# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets

from .. import header
from ..icons import icons
from ..tables import (
    ActivitiesTable,
    DatabasesTable,
    BiosphereFlowsTable,
    ProjectListWidget,
)
from ...signals import signals


class NewInventoryTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(NewInventoryTab, self).__init__(parent)
        # main widgets
        self.projects_widget = ProjectsWidget()
        self.databases_widget = DatabaseWidget()
        self.activities_widget = ActivitiesWidget()
        self.flows_widget = BiosphereFlowsWidget()

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.projects_widget)
        self.overall_layout.addWidget(self.databases_widget)
        self.overall_layout.addWidget(self.activities_widget)
        self.overall_layout.addWidget(self.flows_widget)
        self.setLayout(self.overall_layout)

        self.activities_widget.hide()
        self.flows_widget.hide()

        self.connect_signals()

    def connect_signals(self):
        signals.database_selected.connect(self.update_widgets)

    def update_widgets(self):
        if self.activities_widget.activities_table.rowCount() == 0:
            self.activities_widget.hide()
        else:
            self.activities_widget.show()

        if self.flows_widget.flows_table.rowCount() == 0:
            self.flows_widget.hide()
        else:
            self.flows_widget.show()

class ProjectsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ProjectsWidget, self).__init__()
        self.projects_list = ProjectListWidget()
        # Buttons
        self.new_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.add), 'New')
        self.copy_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.copy), 'Copy current')
        self.delete_project_button = QtWidgets.QPushButton(QtGui.QIcon(icons.delete), 'Delete current')
        # Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(header('Current Project:'))
        self.h_layout.addWidget(self.projects_list)
        self.h_layout.addWidget(self.new_project_button)
        self.h_layout.addWidget(self.copy_project_button)
        self.h_layout.addWidget(self.delete_project_button)
        self.setLayout(self.h_layout)


class DatabaseWidget(QtWidgets.QWidget):
    def __init__(self):
        super(DatabaseWidget, self).__init__()
        self.databases_table = DatabasesTable()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        v_layout.addWidget(header('Databases'))
        v_layout.addWidget(self.databases_table)
        self.setLayout(v_layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Maximum)
        )


class ActivitiesWidget(QtWidgets.QWidget):
    def __init__(self):
        super(ActivitiesWidget, self).__init__()
        self.activities_table = ActivitiesTable()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        v_layout.addWidget(header('Activities'))
        v_layout.addWidget(self.activities_table)
        self.setLayout(v_layout)


class BiosphereFlowsWidget(QtWidgets.QWidget):
    def __init__(self):
        super(BiosphereFlowsWidget, self).__init__()
        self.flows_table = BiosphereFlowsTable()
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.setAlignment(QtCore.Qt.AlignTop)
        v_layout.addWidget(header('Biosphere Flows'))
        v_layout.addWidget(self.flows_table)
        self.setLayout(v_layout)