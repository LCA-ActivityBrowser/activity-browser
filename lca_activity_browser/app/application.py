# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit
from .main_window import MainWindow


class Application(object):
    def __init__(self):
        self.main_window = MainWindow()

    def show(self):
        self.main_window.showMaximized()
