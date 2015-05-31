# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from .controller import Controller
from .ui.main import MainWindow
from PyQt4 import QtCore, QtGui, QtWebKit


class Application(object):
    def __init__(self):
        self.main_window = MainWindow()
        self.controller = Controller(self.main_window)
        self.connect_signals()

    def show(self):
        self.main_window.showMaximized()

    def connect_signals(self):
        self.main_window.right_panel.inventory_tab.connect_signals(self.controller)
        self.main_window.left_panel.cs_tab.connect_signals(self.controller)


        # CFs table -> Add cfs table
        # self.main_window.buttons.new_calculation_setup.clicked.connect(
        #     self.controller.new_calculation_setup
        # )
        # self.main_window.tables.calculation_setups_activities.cellChanged.connect(
        #     self.controller.handle_calculation_setup_activity_table_change
        # )
        # self.main_window.tables.calculation_setups_methods.cellChanged.connect(
        #     self.controller.handle_calculation_setup_method_table_change
        # )
