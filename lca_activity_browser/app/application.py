# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import *
from .controller import Controller
from .ui.main import MainWindow
from PyQt5.QtWidgets import QDesktopWidget

class Application(object):
    def __init__(self):
        self.main_window = MainWindow()
        self.controller = Controller(self.main_window)
        self.connect_signals()

    def show(self):
        self.main_window.show()
        screen = QDesktopWidget().screenGeometry()
        self.main_window.setGeometry(0, 0, screen.width(), screen.height())
        

    def connect_signals(self):
        self.main_window.right_panel.inventory_tab.connect_signals(self.controller)
        self.main_window.left_panel.cs_tab.connect_signals(self.controller)
        self.main_window.toolbar.connect_signals(self.controller)
