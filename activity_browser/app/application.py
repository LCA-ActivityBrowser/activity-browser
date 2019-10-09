# -*- coding: utf-8 -*-
from .controller import Controller
from .ui.main import MainWindow


class Application(object):
    def __init__(self):
        self.main_window = MainWindow()
        self.controller = Controller()

    def show(self):
        self.main_window.showMaximized()

    def close(self):
        self.main_window.close()

    def deleteLater(self):
        self.main_window.deleteLater()
