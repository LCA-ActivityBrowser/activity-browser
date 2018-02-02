# -*- coding: utf-8 -*-
from .controller import Controller
from .ui.main import MainWindow


class Application(object):
    def __init__(self):
        self.main_window = MainWindow()
        self.controller = Controller(self.main_window)

    def show(self):
        self.main_window.showMaximized()