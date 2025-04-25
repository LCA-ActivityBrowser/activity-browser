import pickle
from logging import getLogger

from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals, settings
from activity_browser.ui import icons

from activity_browser.ui.menu_bar import MenuBar

log = getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setWindowIcon(icons.qicons.ab)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.connect_signals()

    def defaultPanes(self):
        from activity_browser.layouts import panes
        return [
            {"class": panes.DatabasesPane, "state": {}},
            {"class": panes.CalculationSetupsPane, "state": {}},
            {"class": panes.ImpactCategoriesPane, "state": {}},
        ]

    def connect_signals(self):
        # Keyboard shortcuts
        signals.project.changed.connect(self.on_project_changed)

    def clearPanes(self):
        for pane in self.panes():
            pane.deleteLater()

    def setPanes(self, panes: list):
        for pane in panes:
            dock_widget = pane(self).getDockWidget(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)
            self.menu_bar.view_menu.addAction(dock_widget.toggleViewAction())

    def panes(self):
        """
        Return a list of all panes in the main window.
        """
        from activity_browser.ui import widgets
        return self.findChildren(widgets.ABAbstractPane)


    def on_project_changed(self, new, old):
        """
        Save the state of the main window, including the current project and layout.
        """
        self.clearPanes()

        self.writeState(old.dir)
        data = self.getState(new.dir)

        for pane in data.get("panes", self.defaultPanes()):
            pane_class = pane.get("class")
            if pane_class is None:
                continue

            log.debug(f"Restoring pane {pane_class.__name__}")

            try:
                pane_instance = pane_class.fromState(pane.get("state"), self)
            except Exception as e:
                log.error(f"Error restoring pane {pane_class.__name__}: {e}")
                continue

            dockwidget = pane_instance.getDockWidget(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockwidget)
            self.menu_bar.view_menu.addAction(dockwidget.toggleViewAction())

            pane_instance.sync()

        success = self.restoreState(data.get("state"), 0)
        log.debug(f"Restored main window state: {success}")

        self.set_titlebar()

    def writeState(self, directory):
        pane_data = []
        for pane in self.panes():
            pane_data.append({
                "class": pane.__class__,
                "state": pane.saveState(),
            })
        own_data = self.saveState(0)

        data = {
            "state": own_data,
            "panes": pane_data,
        }

        # Save the state of the main window
        path = directory.joinpath("activity_browser\\main_window_state.pickle")
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def getState(self, directory):
        """
        Get the state of the main window.
        """
        path = directory.joinpath("activity_browser\\main_window_state.pickle")
        if path.exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
        else:
            data = {
                "state": self.saveState(0),
                "panes": self.defaultPanes(),
            }
        return data


    def set_titlebar(self):
        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")
