# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from .. import Container
from . import horizontal_line, header
from .icons import icons
from .panels import LeftPanel, RightPanel
from .menu_bar import MenuBar
from .statusbar import Statusbar
from .toolbar import Toolbar
from PyQt4 import QtCore, QtGui
from .tabs import (
    ActivityDetailsTab,
    CFsTab,
    InventoryTab,
    MethodsTab,
)
import sip

# Hopefully will end crashes when quitting on OS X
# See http://pyqt.sourceforge.net/Docs/PyQt5/pyqt4_differences.html
sip.setdestroyonexit(False)


class MainWindow(QtGui.QMainWindow):
    DEFAULT_NO_METHOD = 'No method selected yet'

    def __init__(self):
        super(MainWindow, self).__init__(None)

        self.graphics = Container()

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

        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

        self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.left_panel)
        self.splitter_horizontal.addWidget(self.right_panel)
        self.main_horizontal_box.addWidget(self.splitter_horizontal)

        self.vertical_container = QtGui.QVBoxLayout()
        self.vertical_container.addLayout(self.main_horizontal_box)

        self.main_widget = QtGui.QWidget()
        self.main_widget.setLayout(self.vertical_container)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.toolbar = Toolbar(self)
        self.statusbar = Statusbar(self)

        # Debug/working... stack
        working_layout = QtGui.QVBoxLayout()
        working_layout.addWidget(header("Working..."))

        self.working_widget = QtGui.QWidget()
        self.working_widget.setLayout(working_layout)

        self.stacked = QtGui.QStackedWidget()
        self.stacked.addWidget(self.main_widget)
        self.stacked.addWidget(self.working_widget)
        self.setCentralWidget(self.stacked)

    def add_tab_to_panel(self, obj, label, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.addTab(obj, label)

    def select_tab(self, obj, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.setCurrentIndex(panel.indexOf(obj))

    def dialog(self, title, label):
        value, ok = QtGui.QInputDialog.getText(self, title, label)
        if ok:
            return value

    def info(self, label):
        QtGui.QMessageBox.information(
            self,
            "Information",
            label,
            QtGui.QMessageBox.Ok,
        )

    def confirm(self, label):
        response = QtGui.QMessageBox.question(
            self,
            "Confirm Action",
            label,
            QtGui.QMessageBox.Yes,
            QtGui.QMessageBox.No
        )
        return response == QtGui.QMessageBox.Yes
