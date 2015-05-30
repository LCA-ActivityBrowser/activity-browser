# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit
from .main_window import MainWindow
from .controller import Controller


class Application(object):
    def __init__(self):
        self.main_window = MainWindow()
        self.controller = Controller(self.main_window)
        self.connect_signals()

    def show(self):
        self.main_window.showMaximized()

    def connect_signals(self):
        self.main_window.projects_list_widget.currentIndexChanged['QString'].connect(
            self.controller.select_project
        )
        self.main_window.tables.databases.itemDoubleClicked.connect(
            self.controller.select_database
        )
        self.main_window.tables.methods.itemDoubleClicked.connect(
            self.controller.select_method
        )
        self.main_window.tables.activities.itemDoubleClicked.connect(
            self.controller.select_activity
        )
        self.main_window.buttons.new_database.clicked.connect(
            self.controller.add_database
        )
        self.main_window.buttons.new_project.clicked.connect(
            self.controller.new_project
        )
        self.main_window.buttons.delete_project.clicked.connect(
            self.controller.delete_project
        )
        self.main_window.buttons.add_default_data.clicked.connect(
            self.controller.install_default_data
        )
        self.main_window.buttons.new_calculation_setup.clicked.connect(
            self.controller.new_calculation_setup
        )
        self.main_window.actions.delete_database.triggered.connect(
            self.controller.delete_database
        )
