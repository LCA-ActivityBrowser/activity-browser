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
from PyQt5 import QtCore, QtGui, QtWidgets


class MaybeTable(QtWidgets.QWidget):
    searchable = False

    def __init__(self, parent):
        super(MaybeTable, self).__init__(parent)
        self.table = self.TABLE()

        self.no_objects = QtWidgets.QLabel(self.NO)

        inventory_layout = QtWidgets.QVBoxLayout()
        if self.searchable:
            self.search_box = QtWidgets.QLineEdit()
            self.search_box.setPlaceholderText("Filter by search string")
            reset_search_buton = QtWidgets.QPushButton("Reset")

            search_layout = QtWidgets.QHBoxLayout()
            search_layout.setAlignment(QtCore.Qt.AlignLeft)
            search_layout.addWidget(header(self.HEADER))
            search_layout.addWidget(self.search_box)
            search_layout.addWidget(reset_search_buton)

            search_layout_container = QtWidgets.QWidget()
            search_layout_container.setLayout(search_layout)
            inventory_layout.addWidget(search_layout_container)

            reset_search_buton.clicked.connect(self.table.reset_search)
            reset_search_buton.clicked.connect(self.search_box.clear)
            self.search_box.returnPressed.connect(self.set_search_term)
            signals.project_selected.connect(self.search_box.clear)
        else:
            inventory_layout.addWidget(header(self.HEADER))

        inventory_layout.addWidget(self.table)

        self.yes_objects = QtWidgets.QWidget(self)
        self.yes_objects.setLayout(inventory_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.no_objects)
        layout.addWidget(self.yes_objects)
        self.setLayout(layout)

        signals.database_selected.connect(self.choose)

    def set_search_term(self):
        self.table.search(self.search_box.text())

    def choose(self, name):
        self.table.sync(name)
        if self.table.rowCount():
            self.no_objects.hide()
            self.yes_objects.show()
        else:
            self.no_objects.show()
            self.yes_objects.hide()


class MaybeActivitiesTable(MaybeTable):
    NO = 'This database has no technosphere activities'
    TABLE = ActivitiesTableWidget
    HEADER = 'Activities:'
    searchable = True


class MaybeFlowsTable(MaybeTable):
    NO = 'This database has no biosphere flows'
    TABLE = FlowsTableWidget
    HEADER = 'Biosphere flows:'
    searchable = True


class InventoryTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(InventoryTab, self).__init__(parent)
        self.window = parent

        self.databases = DatabasesTableWidget()

        self.activities_table = MaybeActivitiesTable(self)
        self.flows_table = MaybeFlowsTable(self)

        self.add_default_data_button = QtWidgets.QPushButton('Add Default Data (Biosphere flows, LCIA methods)')
        self.new_database_button = QtWidgets.QPushButton('Create New Database')

        no_database_layout = QtWidgets.QVBoxLayout()
        no_database_layout.addWidget(header("No database selected"))
        no_database_layout.addWidget(QtWidgets.QLabel('This section will be filled when a database is selected (double clicked)'))
        no_database_layout.setAlignment(QtCore.Qt.AlignTop)
        self.no_database_container = QtWidgets.QWidget()
        self.no_database_container.setLayout(no_database_layout)

        databases_table_layout = QtWidgets.QHBoxLayout()
        databases_table_layout.addWidget(self.databases)
        databases_table_layout.setAlignment(QtCore.Qt.AlignTop)

        self.databases_table_layout_widget = QtWidgets.QWidget()
        self.databases_table_layout_widget.setLayout(databases_table_layout)

        default_data_button_layout = QtWidgets.QHBoxLayout()
        default_data_button_layout.addWidget(self.add_default_data_button)

        self.default_data_button_layout_widget = QtWidgets.QWidget()
        self.default_data_button_layout_widget.hide()
        self.default_data_button_layout_widget.setLayout(
            default_data_button_layout
        )

        database_header = QtWidgets.QHBoxLayout()
        database_header.setAlignment(QtCore.Qt.AlignLeft)
        database_header.addWidget(header('Databases:'))
        database_header.addWidget(self.new_database_button)

        database_container = QtWidgets.QVBoxLayout()
        database_container.addLayout(database_header)
        database_container.addWidget(
            self.databases_table_layout_widget
        )
        database_container.addWidget(
            self.default_data_button_layout_widget
        )

        inventory_layout = QtWidgets.QVBoxLayout()
        inventory_layout.addWidget(self.activities_table)
        inventory_layout.addWidget(self.flows_table)

        self.inventory_container = QtWidgets.QWidget()
        self.inventory_container.setLayout(inventory_layout)

        activities_container = QtWidgets.QVBoxLayout()
        activities_container.addWidget(self.no_database_container)
        activities_container.addWidget(self.inventory_container)

        # Overall Layout
        tab_container = QtWidgets.QVBoxLayout()
        tab_container.addLayout(database_container)
        tab_container.addLayout(activities_container)
        tab_container.addStretch(1)

        # Context menus (shown on right click)
        self.databases.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.delete_database_action = QtWidgets.QAction(
            QtGui.QIcon(icons.delete), "Delete database", None
        )
        self.databases.addAction(self.delete_database_action)

        self.copy_database_action = QtWidgets.QAction(
            QtGui.QIcon(icons.duplicate), "Copy database", None
        )
        self.databases.addAction(self.copy_database_action)

        self.add_activity_action = QtWidgets.QAction(
            QtGui.QIcon(icons.add), "Add new activity", None
        )
        self.databases.addAction(self.add_activity_action)
        self.add_activity_action.triggered.connect(
            lambda x: signals.new_activity.emit(
                self.databases.currentItem().db_name
            )
        )

        signals.project_selected.connect(self.change_project)
        signals.database_selected.connect(self.change_database)

        self.setLayout(tab_container)

    def connect_signals(self, controller):
        """Signals that alter data and need access to Controller"""
        self.new_database_button.clicked.connect(controller.add_database)
        self.delete_database_action.triggered.connect(controller.delete_database)
        self.copy_database_action.triggered.connect(controller.copy_database)
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
