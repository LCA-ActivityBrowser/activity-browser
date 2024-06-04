# -*- coding: utf-8 -*-
import importlib.util
import shutil
import sys
import traceback

from PySide2 import QtCore, QtGui, QtWidgets

from ..signals import signals
from ..ui.icons import qicons
from ..ui.menu_bar import MenuBar
from ..ui.statusbar import Statusbar
from ..ui.style import header
from .panels import LeftPanel, RightPanel


class MainWindow(QtWidgets.QMainWindow):
    DEFAULT_NO_METHOD = "No method selected yet"

    def __init__(self, parent):
        super(MainWindow, self).__init__(None)

        self.setLocale(
            QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates)
        )
        self.parent = parent

        # Window title
        self.setWindowTitle("Activity Browser")

        # Small icon in main window titlebar
        self.icon = qicons.ab
        self.setWindowIcon(self.icon)

        # Layout
        # The top level element is `central_widget`.
        # Inside is a vertical layout `vertical_container`.
        # Inside the vertical layout is a horizontal layout `main_horizontal_box` with two elements and a
        # The enclosing element is `main_horizontal_box`, which contains the
        # left and right panels `left_panel` and `right_panel`.
        # Left (0) and right (1) panels have a default screen division, set by the setStretchfactor() commands
        # the last argument is the proportion of screen it takes up from total (so 1 and 3 gives 1/4 and 3/4)

        self.main_horizontal_box = QtWidgets.QHBoxLayout()

        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

        # Sets the minimum width for the right panel so scaling on Mac Screens doesnt go out of bounds
        self.right_panel.setMinimumWidth(100)

        self.splitter_horizontal = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.left_panel)
        self.splitter_horizontal.addWidget(self.right_panel)
        self.splitter_horizontal.setStretchFactor(0, 1)
        self.splitter_horizontal.setStretchFactor(1, 3)
        self.main_horizontal_box.addWidget(self.splitter_horizontal)
        self.main_window = QtWidgets.QWidget()
        self.main_window.setLayout(self.main_horizontal_box)
        self.main_window.icon = qicons.main_window
        self.main_window.name = "&Main Window"

        self.setCentralWidget(self.main_window)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.status_bar = Statusbar(self)
        self.setStatusBar(self.status_bar)

        self.connect_signals()

    def closeEvent(self, event):
        self.parent.close()

    def connect_signals(self):
        # Keyboard shortcuts
        signals.restore_cursor.connect(self.restore_user_control)

    def add_tab_to_panel(self, obj, label, side):
        panel = self.left_panel if side == "left" else self.right_panel
        panel.add_tab(obj, label)

    def select_tab(self, obj, side):
        panel = self.left_panel if side == "left" else self.right_panel
        panel.setCurrentIndex(panel.indexOf(obj))

    def dialog(self, title, label):
        value, ok = QtWidgets.QInputDialog.getText(self, title, label)
        if ok:
            return value

    def info(self, label):
        QtWidgets.QMessageBox.information(
            self,
            "Information",
            label,
            QtWidgets.QMessageBox.Ok,
        )

    def warning(self, title, text):
        QtWidgets.QMessageBox.warning(self, title, text)

    def confirm(self, label):
        response = QtWidgets.QMessageBox.question(
            self,
            "Confirm Action",
            label,
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        return response == QtWidgets.QMessageBox.Yes

    def restore_user_control(self):
        QtWidgets.QApplication.restoreOverrideCursor()
