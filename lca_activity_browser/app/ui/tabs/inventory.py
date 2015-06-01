# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ..tables import (
    ActivitiesTableWidget,
    DatabasesTableWidget,
    FlowsTableWidget,
    ProjectListWidget,
)
from .. import horizontal_line, header
from ...signals import signals
from ..icons import icons
from brightway2 import *
from PyQt4 import QtCore, QtGui


class MaybeTable(QtGui.QWidget):
    def __init__(self, parent):
        super(MaybeTable, self).__init__(parent)
        self.table = self.TABLE()

        self.no_activities = QtGui.QLabel(self.NO)

        inventory_layout = QtGui.QVBoxLayout()
        inventory_layout.addWidget(header(self.HEADER))
        inventory_layout.addWidget(horizontal_line())
        inventory_layout.addWidget(self.table)

        self.yes_activities = QtGui.QWidget(self)
        self.yes_activities.setLayout(inventory_layout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.no_activities)
        layout.addWidget(self.yes_activities)
        self.setLayout(layout)

        signals.database_selected.connect(self.choose)

    def choose(self, name):
        self.table.sync(name)
        if self.table.rowCount():
            self.no_activities.hide()
            self.yes_activities.show()
        else:
            self.no_activities.show()
            self.yes_activities.hide()


class MaybeActivitiesTable(MaybeTable):
    NO = 'This database has no technosphere activities'
    TABLE = ActivitiesTableWidget
    HEADER = 'Activities:'


class MaybeFlowsTable(MaybeTable):
    NO = 'This database has no biosphere flows'
    TABLE = FlowsTableWidget
    HEADER = 'Biosphere flows:'


class InventoryTab(QtGui.QWidget):
    def __init__(self, parent):
        super(InventoryTab, self).__init__(parent)
        self.window = parent

        self.databases = DatabasesTableWidget()

        # Not visible when instantiated
        self.flows = FlowsTableWidget()

        self.add_default_data_button = QtGui.QPushButton('Add Default Data (Biosphere flows, LCIA methods)')
        self.new_database_button = QtGui.QPushButton('Create New Database')

        no_database_layout = QtGui.QVBoxLayout()
        no_database_layout.addWidget(header("No database selected"))
        no_database_layout.addWidget(QtGui.QLabel('This section will be filled when a database is selected (double clicked)'))
        no_database_layout.setAlignment(QtCore.Qt.AlignTop)
        self.no_database_container = QtGui.QWidget()
        self.no_database_container.setLayout(no_database_layout)

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
        inventory_layout.addWidget(MaybeActivitiesTable(self))
        inventory_layout.addWidget(MaybeFlowsTable(self))

        self.inventory_container = QtGui.QWidget()
        self.inventory_container.setLayout(inventory_layout)

        activities_container = QtGui.QVBoxLayout()
        activities_container.addWidget(self.no_database_container)
        activities_container.addWidget(self.inventory_container)

        # Overall Layout
        tab_container = QtGui.QVBoxLayout()
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
        self.new_database_button.clicked.connect(controller.add_database)
        self.delete_database_action.triggered.connect(controller.delete_database)
        self.add_default_data_button.clicked.connect(controller.install_default_data)

    def change_project(self, name):
        self.databases.sync()

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
