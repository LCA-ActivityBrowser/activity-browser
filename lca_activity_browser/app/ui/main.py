# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import Container
from ..calculation_setups import (
    CSActivityTableWidget,
    CSListWidget,
    CSMethodsTableWidget,
)
from ..databases_table import (
    ActivitiesTableWidget,
    DatabasesTableWidget,
    FlowsTableWidget,
)
from ..graphics import Canvas
from . import horizontal_line, header
from .icons import icons
from .menu_bar import MenuBar
from ..methods import MethodsTableWidget, CFsTableWidget
from ..projects import ProjectListWidget
from .statusbar import Statusbar
from .toolbar import Toolbar
from PyQt4 import QtCore, QtGui, QtWebKit
from .tabs import InventoryTab


class MainWindow(QtGui.QMainWindow):
    DEFAULT_NO_METHOD = 'No method selected yet'

    def __init__(self):
        super(MainWindow, self).__init__(None)

        self.buttons = Container()
        self.labels = Container()
        self.graphics = Container()
        self.tables = Container()
        self.actions = Container()

        # Window title
        self.setWindowTitle("Activity Browser")

        # Small icon in main window titlebar
        self.icon = QtGui.QIcon(icons.pony)
        self.setWindowIcon(self.icon)

        # Clipboard
        self.clip = QtGui.QApplication.clipboard()

        # Layout
        # The top level element is `central_widget`.
        # Inside is a vertical layout `vertical_container`.
        # Inside the vertical layout is a horizontal layout `main_horizontal_box` with two elements and a
        # The enclosing element is `main_horizontal_box`, which contains the
        # left and right panels `left_panel` and `right_panel`.

        self.main_horizontal_box = QtGui.QHBoxLayout()

        self.left_panel = self.build_left_panel()
        self.right_panel = self.build_right_panel()

        self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.left_panel)
        self.splitter_horizontal.addWidget(self.right_panel)
        self.main_horizontal_box.addWidget(self.splitter_horizontal)

        self.vertical_container = QtGui.QVBoxLayout()
        self.vertical_container.addLayout(self.main_horizontal_box)

        self.central_widget = QtGui.QWidget()
        self.central_widget.setLayout(self.vertical_container)
        self.setCentralWidget(self.central_widget)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.toolbar = Toolbar(self)
        self.statusbar = Statusbar(self)

    def add_tab_to_panel(self, obj, label, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.addTab(obj, label)

    def select_tab(self, obj, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.setCurrentIndex(panel.indexOf(obj))

    def build_right_panel(self):
        panel = QtGui.QTabWidget()
        panel.setMovable(True)

        self.inventory_tab = InventoryTab(self)
        self.methods_tab_container = self.build_methods_tab()
        panel.addTab(self.inventory_tab, 'Inventory')
        panel.addTab(self.methods_tab_container, 'Impact Assessment')

        return panel

    def build_left_panel(self):
        panel = QtGui.QTabWidget()
        panel.setMovable(True)

        self.activity_tab_container = self.build_activity_tab()
        self.cfs_tab_container = self.build_cfs_tab()
        self.cs_tab_container = self.build_calculation_setup_tab()
        panel.addTab(self.activity_tab_container, 'Activity')
        panel.addTab(self.cfs_tab_container, 'LCIA CFs')
        panel.addTab(self.cs_tab_container, 'LCA Calculations')

        return panel

    def dialog(self, title, label):
        value, ok = QtGui.QInputDialog.getText(self, title, label)
        if ok:
            return value

    def confirm(self, label):
        response = QtGui.QMessageBox.question(
            self,
            "Confirm Action",
            label,
            QtGui.QMessageBox.Yes,
            QtGui.QMessageBox.No
        )
        return response == QtGui.QMessageBox.Yes

    def build_activity_tab(self):
        self.labels.no_activity = QtGui.QLabel('No activity selected yet')
        self.labels.no_consumption = QtGui.QLabel("No activities consume the reference product of this activity.")
        self.labels.no_consumption.hide()

        self.graphics.lobby1 = Canvas()
        self.graphics.lobby2 = Canvas()

        activity_container = QtGui.QVBoxLayout()
        activity_container.setAlignment(QtCore.Qt.AlignTop)
        activity_container.addWidget(self.labels.no_activity)
        activity_container.addWidget(self.labels.no_consumption)
        activity_container.addWidget(self.graphics.lobby1)
        activity_container.addWidget(self.graphics.lobby2)

        containing_widget = QtGui.QWidget()
        containing_widget.setLayout(activity_container)
        return containing_widget

    def build_calculation_setup_tab(self):
        self.tables.calculation_setups_activities = CSActivityTableWidget()
        self.tables.calculation_setups_methods = CSMethodsTableWidget()
        self.calculation_setups_list = CSListWidget()

        self.buttons.new_calculation_setup = QtGui.QPushButton('New calculation setup')
        self.buttons.rename_calculation_setup = QtGui.QPushButton('Rename this setup')
        self.buttons.delete_calculation_setup = QtGui.QPushButton('Delete this setup')

        name_row = QtGui.QHBoxLayout()
        name_row.addWidget(header('Calculation Setups:'))
        name_row.addWidget(self.calculation_setups_list)
        name_row.addWidget(self.buttons.new_calculation_setup)
        name_row.addWidget(self.buttons.rename_calculation_setup)
        name_row.addWidget(self.buttons.delete_calculation_setup)

        container = QtGui.QVBoxLayout()
        container.addLayout(name_row)
        container.addWidget(horizontal_line())
        container.addWidget(header('Products and amounts:'))
        container.addWidget(self.tables.calculation_setups_activities)
        container.addWidget(horizontal_line())
        container.addWidget(header('LCIA Methods:'))
        container.addWidget(self.tables.calculation_setups_methods)

        widget = QtGui.QWidget()
        widget.setLayout(container)
        return widget

    def build_methods_tab(self):
        self.tables.methods = MethodsTableWidget()
        container = QtGui.QVBoxLayout()
        container.addWidget(header('LCIA Methods:'))
        container.addWidget(horizontal_line())
        container.addWidget(self.tables.methods)
        widget = QtGui.QWidget()
        widget.setLayout(container)
        return widget

    def build_cfs_tab(self):
        # Not visible when instantiated
        self.tables.cfs = CFsTableWidget()

        self.labels.no_method = QtGui.QLabel(self.DEFAULT_NO_METHOD)

        container = QtGui.QVBoxLayout()
        container.addWidget(header('Characterization Factors:'))
        container.addWidget(horizontal_line())
        container.addWidget(self.labels.no_method)
        container.addWidget(self.tables.cfs)
        container.setAlignment(QtCore.Qt.AlignTop)
        widget = QtGui.QWidget()
        widget.setLayout(container)
        return widget

    def add_right_inventory_tables(self, database):
        self.labels.no_database.hide()
        self.tables.activities.clear()
        self.tables.activities.sync(database)
        self.tables.flows.clear()
        self.tables.flows.sync(database)
        self.tables.activities.show()
        self.tables.flows.show()

    def hide_right_inventory_tables(self):
        self.tables.flows.hide()
        self.tables.flows.clear()
        self.tables.activities.hide()
        self.tables.activities.clear()
        self.labels.no_database.show()

    def add_cfs_table(self, method):
        self.labels.no_method.setText(
            "Method: " + ";".join(method)
        )
        self.tables.cfs.sync(method)
        self.tables.cfs.show()

    def hide_cfs_table(self):
        self.tables.cfs.hide()
        self.tables.cfs.clear()
        self.labels.no_method.setText(self.DEFAULT_NO_METHOD)
