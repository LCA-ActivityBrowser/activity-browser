# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit
from .icons import icons
from .menu_bar import MenuBar
from .toolbar import Toolbar
from .statusbar import Statusbar
import sys


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

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

        self.left_panel = QtGui.QTabWidget()
        self.right_panel = QtGui.QTabWidget()
        self.left_panel.setMovable(True)
        self.right_panel.setMovable(True)

        self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.left_panel)
        self.splitter_horizontal.addWidget(self.right_panel)
        self.main_horizontal_box.addWidget(self.splitter_horizontal)

        self.vertical_container = QtGui.QVBoxLayout()
        self.vertical_container.addLayout(self.main_horizontal_box)

        self.central_widget = QtGui.QWidget()
        self.central_widget.setLayout(self.vertical_container)
        self.setCentralWidget(self.central_widget)

        # # EXCEPT FOR THIS BLOCK:
        # # set up standard widgets in docks
        self.menu_bar = MenuBar(self)
        self.toolbar = Toolbar(self)
        self.statusbar = Statusbar(self)
        # self.set_up_standard_widgets()

        # # at program start
        # self.listDatabases()
        # self.listProjects()


def run_activity_browser():
    app = QtGui.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    sys.exit(app.exec_())
