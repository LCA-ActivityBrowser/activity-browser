# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals
from activity_browser.layouts import panes
from activity_browser.ui import widgets, icons

from ..ui.icons import qicons
from ..ui.menu_bar import MenuBar
from ..ui.statusbar import Statusbar
from .panels import RightPanel


class MainWindow(QtWidgets.QMainWindow):
    panes = [panes.Databases, panes.ImpactCategories, panes.CalculationSetupsPane]

    def __init__(self):
        super().__init__()

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setWindowIcon(icons.qicons.ab)

        self.right_panel = RightPanel(self)
        self.setCentralWidget(self.right_panel)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.status_bar = Statusbar(self)
        self.setStatusBar(self.status_bar)
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
        self.setDockOptions(QtWidgets.QMainWindow.GroupedDragging | QtWidgets.QMainWindow.AllowTabbedDocks | QtWidgets.QMainWindow.AllowNestedDocks)

        dock_widget = widgets.ABDockWidget("Databases", self, widgets.ABDockWidget.HideMode.Hide)
        dock_widget.setWidget(panes.Databases(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        dock_widget = widgets.ABDockWidget("Calculation Setups", self, widgets.ABDockWidget.HideMode.Hide)
        dock_widget.setWidget(panes.CalculationSetupsPane(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        dock_widget = widgets.ABDockWidget("Impact Categories", self, widgets.ABDockWidget.HideMode.Hide)
        dock_widget.setWidget(panes.ImpactCategories(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        self.connect_signals()

    def connect_signals(self):
        # Keyboard shortcuts
        signals.restore_cursor.connect(self.restore_user_control)

        signals.project.changed.connect(self.set_titlebar)

    def set_titlebar(self):
        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")

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

    def dialog_on_exception(self, exception: Exception):
        QtWidgets.QMessageBox.critical(
            self,
            f"An error occurred: {type(exception).__name__}",
            f"An error occurred, check the logs for more information \n\n {str(exception)}",
            QtWidgets.QMessageBox.Ok,
        )

