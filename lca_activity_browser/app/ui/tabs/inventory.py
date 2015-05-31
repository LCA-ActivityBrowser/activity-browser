# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..tables import (
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

        self.projects_list_widget = ProjectListWidget()
        self.databases = DatabasesTableWidget()

        # Not visible when instantiated
        self.activities = ActivitiesTableWidget()
        self.flows = FlowsTableWidget()

        self.add_default_data_button = QtGui.QPushButton('Add Default Data (Biosphere flows, LCIA methods)')
        self.new_project_button = QtGui.QPushButton('Create New Project')
        self.copy_project_button = QtGui.QPushButton('Copy Current Project')
        self.delete_project_button = QtGui.QPushButton('Delete Current Project')
        self.new_database_button = QtGui.QPushButton('Create New Database')
        self.no_database_label = QtGui.QLabel('No database selected yet')

        projects_list_layout = QtGui.QHBoxLayout()
        projects_list_layout.setAlignment(QtCore.Qt.AlignLeft)
        projects_list_layout.addWidget(QtGui.QLabel('Current Project:'))
        projects_list_layout.addWidget(self.
            projects_list_widget)

        projects_button_line = QtGui.QHBoxLayout()
        projects_button_line.addWidget(header('Projects:'))
        projects_button_line.addWidget(self.new_project_button)
        projects_button_line.addWidget(self.copy_project_button)
        projects_button_line.addWidget(self.delete_project_button)

        project_container = QtGui.QVBoxLayout()
        project_container.addLayout(projects_button_line)
        project_container.addWidget(horizontal_line())
        project_container.addLayout(projects_list_layout)

        databases_table_layout = QtGui.QHBoxLayout()
        databases_table_layout.addWidget(QtGui.QLabel('Databases:'))
        databases_table_layout.addWidget(self.databases)
        databases_table_layout.addWidget(self.new_database_button)
        databases_table_layout.setAlignment(QtCore.Qt.AlignTop)

        databases_table_layout_widget = QtGui.QWidget()
        databases_table_layout_widget.setLayout(databases_table_layout)

        default_data_button_layout = QtGui.QHBoxLayout()
        default_data_button_layout.addWidget(self.add_default_data_button)

        default_data_button_layout_widget = QtGui.QWidget()
        default_data_button_layout_widget.hide()
        default_data_button_layout_widget.setLayout(
            default_data_button_layout
        )

        database_container = QtGui.QVBoxLayout()
        database_container.addWidget(header('Databases:'))
        database_container.addWidget(horizontal_line())
        database_container.addWidget(databases_table_layout_widget)
        database_container.addWidget(default_data_button_layout_widget)

        activities_container = QtGui.QVBoxLayout()
        activities_container.addWidget(header('Activities:'))
        activities_container.addWidget(horizontal_line())
        activities_container.addWidget(self.no_database_label)
        activities_container.addWidget(self.activities)
        activities_container.addWidget(header('Biosphere Flows:'))
        activities_container.addWidget(horizontal_line())
        activities_container.addWidget(self.no_database_label)
        activities_container.addWidget(self.flows)

        # Overall Layout
        tab_container = QtGui.QVBoxLayout()
        tab_container.addLayout(project_container)
        tab_container.addLayout(database_container)
        tab_container.addLayout(activities_container)
        tab_container.addStretch(1)

        # Context menus (shown on right click)
        self.databases.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.delete_database_action = QtGui.QAction(
            QtGui.QIcon(icons.delete), "Delete database", None
        )
        self.databases.addAction(self.delete_database_action)

        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.change_database)

        self.setLayout(tab_container)

    def connect_signals(self, controller):
        """Signals that alter data and need access to Controller"""
        self.projects_list_widget.currentIndexChanged['QString'].connect(
            controller.select_project
        )

    def change_project(self, name):
        index = sorted([project.name for project in projects]).index(projects.project)
        self.projects_list_widget.setCurrentIndex(index)
        self.databases.sync()

        self.flows.hide()
        self.flows.clear()
        self.activities.hide()
        self.activities.clear()
        self.no_database_label.show()

        if not len(databases):
            self.default_data_button_layout_widget.show()
            self.databases_table_layout_widget.hide()
        else:
            self.default_data_button_layout_widget.hide()
            self.databases_table_layout_widget.show()

    def change_database(self, name):
        self.no_database_label.hide()
        self.activities.show()
        self.flows.show()
