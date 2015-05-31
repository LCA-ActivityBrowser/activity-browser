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

        no_database_layout = QtGui.QVBoxLayout()
        no_database_layout.addWidget(header("No database selected"))
        no_database_layout.addWidget(QtGui.QLabel('This section will be filled when a database is selected (double clicked)'))
        no_database_layout.setAlignment(QtCore.Qt.AlignTop)
        self.no_database_container = QtGui.QWidget()
        self.no_database_container.setLayout(no_database_layout)

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
        project_container.addLayout(projects_list_layout)

        databases_table_layout = QtGui.QHBoxLayout()
        databases_table_layout.addWidget(self.databases)
        databases_table_layout.setAlignment(QtCore.Qt.AlignTop)

        self.databases_table_layout_widget = QtGui.QWidget()
        self.databases_table_layout_widget.setLayout(databases_table_layout)

        default_data_button_layout = QtGui.QHBoxLayout()
        default_data_button_layout.addWidget(self.add_default_data_button)

        self.default_data_button_layout_widget = QtGui.QWidget()
        self.default_data_button_layout_widget.hide()
        self.default_data_button_layout_widget.setLayout(
            default_data_button_layout
        )

        database_header = QtGui.QHBoxLayout()
        database_header.setAlignment(QtCore.Qt.AlignLeft)
        database_header.addWidget(header('Databases:'))
        database_header.addWidget(self.new_database_button)

        database_container = QtGui.QVBoxLayout()
        database_container.addWidget(horizontal_line())
        database_container.addLayout(database_header)
        database_container.addWidget(
            self.databases_table_layout_widget
        )
        database_container.addWidget(
            self.default_data_button_layout_widget
        )

        inventory_layout = QtGui.QVBoxLayout()
        inventory_layout.addWidget(header('Activities:'))
        inventory_layout.addWidget(horizontal_line())
        inventory_layout.addWidget(self.activities)
        inventory_layout.addWidget(header('Biosphere Flows:'))
        inventory_layout.addWidget(horizontal_line())
        inventory_layout.addWidget(self.flows)

        self.inventory_container = QtGui.QWidget()
        self.inventory_container.setLayout(inventory_layout)

        activities_container = QtGui.QVBoxLayout()
        activities_container.addWidget(self.no_database_container)
        activities_container.addWidget(self.inventory_container)

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
        self.new_project_button.clicked.connect(controller.new_project)
        self.delete_project_button.clicked.connect(controller.delete_project)
        self.new_database_button.clicked.connect(controller.add_database)
        self.delete_database_action.triggered.connect(controller.delete_database)
        self.add_default_data_button.clicked.connect(controller.install_default_data)

    def change_project(self, name):
        index = sorted([project.name for project in projects]).index(projects.project)
        self.projects_list_widget.setCurrentIndex(index)
        self.databases.sync()

        self.flows.clear()
        self.activities.clear()
        self.no_database_container.show()
        self.inventory_container.hide()

        if not len(databases):
            self.default_data_button_layout_widget.show()
            self.databases_table_layout_widget.hide()
        else:
            self.default_data_button_layout_widget.hide()
            self.databases_table_layout_widget.show()

    def change_database(self, name):
        self.no_database_container.hide()
        self.inventory_container.show()
