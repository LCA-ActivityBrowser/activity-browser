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
        self.main_window.table_databases.doubleClicked.connect(
            self.controller.select_database
        )
        self.main_window.buttons.new_database.clicked.connect(
            self.controller.add_database
        )
