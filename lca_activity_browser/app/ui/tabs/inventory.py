# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...databases_table import (
    ActivitiesTableWidget,
    DatabasesTableWidget,
    FlowsTableWidget,
)
from .. import horizontal_line, header
from ...projects import ProjectListWidget
from ...signals import signals
from ..icons import icons
from brightway2 import *
from PyQt4 import QtCore, QtGui


class InventoryTab(QtGui.QWidget):
    def __init__(self, parent):
        super(InventoryTab, self).__init__(parent)
        self.window = parent

        self.window.projects_list_widget = ProjectListWidget()
        self.window.tables.databases = DatabasesTableWidget()

        # Not visible when instantiated
        self.window.tables.activities = ActivitiesTableWidget()
        self.window.tables.flows = FlowsTableWidget()

        self.window.buttons.add_default_data = QtGui.QPushButton('Add Default Data (Biosphere flows, LCIA methods)')
        self.window.buttons.new_project = QtGui.QPushButton('Create New Project')
        self.window.buttons.copy_project = QtGui.QPushButton('Copy Current Project')
        self.window.buttons.delete_project = QtGui.QPushButton('Delete Current Project')
        self.window.buttons.new_database = QtGui.QPushButton('Create New Database')
        self.window.labels.no_database = QtGui.QLabel('No database selected yet')

        projects_list_layout = QtGui.QHBoxLayout()
        projects_list_layout.setAlignment(QtCore.Qt.AlignLeft)
        projects_list_layout.addWidget(QtGui.QLabel('Current Project:'))
        projects_list_layout.addWidget(self.window.projects_list_widget)

        projects_button_line = QtGui.QHBoxLayout()
        projects_button_line.addWidget(header('Projects:'))
        projects_button_line.addWidget(self.window.buttons.new_project)
        projects_button_line.addWidget(self.window.buttons.copy_project)
        projects_button_line.addWidget(self.window.buttons.delete_project)

        project_container = QtGui.QVBoxLayout()
        project_container.addLayout(projects_button_line)
        project_container.addWidget(horizontal_line())
        project_container.addLayout(projects_list_layout)

        databases_table_layout = QtGui.QHBoxLayout()
        databases_table_layout.addWidget(QtGui.QLabel('Databases:'))
        databases_table_layout.addWidget(self.window.tables.databases)
        databases_table_layout.addWidget(self.window.buttons.new_database)
        databases_table_layout.setAlignment(QtCore.Qt.AlignTop)

        self.window.databases_table_layout_widget = QtGui.QWidget()
        self.window.databases_table_layout_widget.setLayout(
            databases_table_layout
        )

        default_data_button_layout = QtGui.QHBoxLayout()
        default_data_button_layout.addWidget(self.window.buttons.add_default_data)

        self.window.default_data_button_layout_widget = QtGui.QWidget()
        self.window.default_data_button_layout_widget.hide()
        self.window.default_data_button_layout_widget.setLayout(
            default_data_button_layout
        )

        database_container = QtGui.QVBoxLayout()
        database_container.addWidget(header('Databases:'))
        database_container.addWidget(horizontal_line())
        database_container.addWidget(
            self.window.databases_table_layout_widget
        )
        database_container.addWidget(
            self.window.default_data_button_layout_widget
        )

        activities_container = QtGui.QVBoxLayout()
        activities_container.addWidget(header('Activities:'))
        activities_container.addWidget(horizontal_line())
        activities_container.addWidget(self.window.labels.no_database)
        activities_container.addWidget(self.window.tables.activities)
        activities_container.addWidget(header('Biosphere Flows:'))
        activities_container.addWidget(horizontal_line())
        activities_container.addWidget(self.window.labels.no_database)
        activities_container.addWidget(self.window.tables.flows)

        # Overall Layout
        tab_container = QtGui.QVBoxLayout()
        tab_container.addLayout(project_container)
        tab_container.addLayout(database_container)
        tab_container.addLayout(activities_container)
        tab_container.addStretch(1)

        # Context menus (shown on right click)
        self.window.tables.databases.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.window.actions.delete_database = QtGui.QAction(
            QtGui.QIcon(icons.delete), "Delete database", None
        )
        self.window.tables.databases.addAction(self.window.actions.delete_database)

        signals.project_changed.connect(self.change_project)

        self.setLayout(tab_container)

    def connect_signals(self, controller):
        self.window.projects_list_widget.currentIndexChanged['QString'].connect(
            controller.select_project
        )

    def change_project(self, name):
        index = sorted([project.name for project in projects]).index(projects.project)
        self.window.projects_list_widget.setCurrentIndex(index)
        self.window.tables.databases.sync()

        self.window.tables.flows.hide()
        self.window.tables.flows.clear()
        self.window.tables.activities.hide()
        self.window.tables.activities.clear()
        self.window.labels.no_database.show()

        if not len(databases):
            self.window.default_data_button_layout_widget.show()
            self.window.databases_table_layout_widget.hide()
        else:
            self.window.default_data_button_layout_widget.hide()
            self.window.databases_table_layout_widget.show()
