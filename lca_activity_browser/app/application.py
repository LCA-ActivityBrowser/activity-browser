# -*- coding: utf-8 -*-
from .controller import Controller
from .ui.main import MainWindow


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
        self.main_window.toolbar.connect_signals(self.controller)
