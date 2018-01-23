# -*- coding: utf-8 -*-
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from .style import header
from .icons import icons
from .menu_bar import MenuBar
from .panels import LeftPanel, RightPanel
from .statusbar import Statusbar
from .toolbar import Toolbar
from .utils import StdRedirector
from ..signals import signals


class MainWindow(QtWidgets.QMainWindow):
    DEFAULT_NO_METHOD = 'No method selected yet'

    def __init__(self):
        super(MainWindow, self).__init__(None)

        # Window title
        self.setWindowTitle("Activity Browser")

        # Background Color
        # self.setAutoFillBackground(True)
        # p = self.palette()
        # p.setColor(self.backgroundRole(), QtGui.QColor(148, 143, 143, 127))
        # self.setPalette(p)

        # Small icon in main window titlebar
        self.icon = QtGui.QIcon(icons.ab)
        self.setWindowIcon(self.icon)

        # Clipboard
        self.clipboard = QtWidgets.QApplication.clipboard()

        # Layout
        # The top level element is `central_widget`.
        # Inside is a vertical layout `vertical_container`.
        # Inside the vertical layout is a horizontal layout `main_horizontal_box` with two elements and a
        # The enclosing element is `main_horizontal_box`, which contains the
        # left and right panels `left_panel` and `right_panel`.

        self.main_horizontal_box = QtWidgets.QHBoxLayout()

        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

        self.splitter_horizontal = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter_horizontal.addWidget(self.left_panel)
        self.splitter_horizontal.addWidget(self.right_panel)
        self.main_horizontal_box.addWidget(self.splitter_horizontal)

        self.vertical_container = QtWidgets.QVBoxLayout()
        self.vertical_container.addLayout(self.main_horizontal_box)

        self.main_widget = QtWidgets.QWidget()
        self.main_widget.setLayout(self.vertical_container)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.toolbar = Toolbar(self)
        self.statusbar = Statusbar(self)

        # Debug/working... stack
        self.log = QtWidgets.QTextEdit(self)
        sys.stdout = StdRedirector(self.log, sys.stdout, None)
        sys.stderr = StdRedirector(self.log, sys.stderr, "blue")

        working_layout = QtWidgets.QVBoxLayout()
        working_layout.addWidget(header("Program output:"))
        working_layout.addWidget(self.log)

        self.working_widget = QtWidgets.QWidget()
        self.working_widget.setLayout(working_layout)

        self.stacked = QtWidgets.QStackedWidget()
        self.stacked.addWidget(self.main_widget)
        self.stacked.addWidget(self.working_widget)
        self.setCentralWidget(self.stacked)

        self.connect_signals()

    def connect_signals(self):
        signals.copy_selection_to_clipboard.connect(self.set_clipboard_text)

    def add_tab_to_panel(self, obj, label, side):
        panel = self.left_panel if side == 'left' else self.right_panel
        panel.addTab(obj, label)

    def select_tab(self, obj, side):
        panel = self.left_panel if side == 'left' else self.right_panel
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
            QtWidgets.QMessageBox.No
        )
        return response == QtWidgets.QMessageBox.Yes

    @QtCore.pyqtSlot(str)
    def set_clipboard_text(self, clipboard_text):
        self.clipboard.setText(clipboard_text)
