# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import signals
from activity_browser.layouts import panes

from ..ui.icons import qicons
from ..ui.menu_bar import MenuBar
from ..ui.statusbar import Statusbar
from .panels import LeftPanel, RightPanel


class MainWindow(QtWidgets.QMainWindow):
    panes = [panes.Databases, panes.ImpactCategories, panes.CalculationSetupsPane]

    def __init__(self):
        super().__init__()

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setWindowIcon(qicons.ab)

        self.right_panel = RightPanel(self)
        self.setCentralWidget(self.right_panel)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.status_bar = Statusbar(self)
        self.setStatusBar(self.status_bar)
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)
        self.setDockOptions(QtWidgets.QMainWindow.GroupedDragging | QtWidgets.QMainWindow.AllowTabbedDocks | QtWidgets.QMainWindow.AllowNestedDocks)

        dock_widget = DockWidget("Databases", self)
        dock_widget.setWidget(panes.Databases(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        dock_widget = DockWidget("Calculation Setups", self)
        dock_widget.setWidget(panes.CalculationSetupsPane(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        dock_widget = DockWidget("Impact Categories", self)
        dock_widget.setWidget(panes.ImpactCategories(self))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

        self.connect_signals()

    def closeEvent(self, event):
        self.parent.close()

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


class DockWidget(QtWidgets.QDockWidget):
    def __init__(self, title: str, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(title, parent)
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.visibilityChanged.connect(self.on_visibility_changed)
        self.dockLocationChanged.connect(self.on_dock_location_changed)

    def on_visibility_changed(self, is_visible: bool) -> None:
        # this visibility monitor is really only needed to detect merges of
        # tabbed, floating windows with existing docked windows
        if not is_visible and isinstance(self.parent(), QtWidgets.QMainWindow):
            main_window: QtWidgets.QMainWindow = self.parent()
            all_dockwidgets: list[QtWidgets.QDockWidget] = main_window.findChildren(QtWidgets.QDockWidget)
            for dockwidget in all_dockwidgets:
                if hasattr(dockwidget, 'on_dock_location_changed'):
                    dockwidget.on_dock_location_changed(main_window.dockWidgetArea(dockwidget), False)

    def on_dock_location_changed(self, area: Qt.DockWidgetArea, update_others: bool = True) -> None:
        main_window = self.parent()
        if not isinstance(main_window, QtWidgets.QMainWindow):
            # mysterious parents call for a title
            self.setTitleBarWidget(TitleBar(self.windowTitle(), self))
            return

        if not main_window.tabifiedDockWidgets(self):
            # if there's no siblings we ain't a tab!
            self.setTitleBarWidget(TitleBar(self.windowTitle(), self))

            if not update_others:
                # prevent infinite recursion
                return

            # force an update to all other docks that may now no longer be tabs
            all_dockwidgets: list[QtWidgets.QDockWidget] = main_window.findChildren(QtWidgets.QDockWidget)
            for dockwidget in all_dockwidgets:
                if dockwidget != self and hasattr(dockwidget, 'on_dock_location_changed'):
                    dockwidget.on_dock_location_changed(main_window.dockWidgetArea(dockwidget), False)
            return

        # at this point the dockwidget is either a resting tab or a tab
        # that is being dragged and hasn't been dropped yet (siblings are updated post-drop)
        # collect all siblings of this dockwidget...
        tab_siblings: list[QtWidgets.QDockWidget] = main_window.tabifiedDockWidgets(self)
        # and filter for non-floating siblings in the same area
        tab_siblings = [x for x in tab_siblings if main_window.dockWidgetArea(x) == area and not x.isFloating()]

        if tab_siblings:
            if not isinstance(self.titleBarWidget(), TitleBar):
                # no changes needed, prevent infinite recursion
                return

            # show a title if we're not floating (this tab is settled),
            # hide it otherwise (this tab just became floating but wasn't dropped)
            self.setTitleBarWidget(QtWidgets.QWidget() if not self.isFloating() else TitleBar(self.windowTitle(), self))

            # in this case it's also a good idea to tell to reconsider their situation
            # since Qt won't notify them separately
            for sibling in tab_siblings:
                if hasattr(sibling, 'on_dock_location_changed'):
                    sibling.on_dock_location_changed(main_window.dockWidgetArea(sibling), True)
        else:
            self.setTitleBarWidget(TitleBar(self.windowTitle(), self))


class TitleBar(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel(title, self)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)



