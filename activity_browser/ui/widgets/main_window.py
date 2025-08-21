import pickle
from logging import getLogger

from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals, application
from activity_browser.ui import icons

from activity_browser.ui.menu_bar import MenuBar

log = getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setDockNestingEnabled(True)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.connect_signals()

    def sync(self):
        """
        Synchronizes the main window layout with the current Brightway2 project.

        This method clears existing panes, initializes default panes, and arranges them
        in the main window. Hidden panes are set to be invisible, and the first pane is
        raised to the top. The window title is updated to reflect the current project.

        Steps:
        - Clear all existing panes.
        - Create and add default panes as dock widgets.
        - Hide panes that are marked as hidden.
        - Tabify dock widgets for better organization.
        - Raise the first dock widget to the top.
        - Update the window title with the current project name.

        Args:
            self: The instance of the MainWindow class.
        """
        from activity_browser.layouts import panes

        # Clear all existing panes in the main window
        self.clearPanes()

        dws = []
        # Iterate through the default panes and add them as dock widgets
        for pane_class in panes.default_panes:
            pane = pane_class(parent=self)
            dockwidget = pane.getDockWidget(self)
            dws.append(dockwidget)

            # Add the dock widget to the left dock area
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockwidget)
            # Add the toggle view action to the menu bar
            self.menu_bar.view_menu.addAction(dockwidget.toggleViewAction())

            # Hide the dock widget if it is marked as hidden
            if pane_class in panes.hidden_panes:
                dockwidget.hide()

            # Synchronize the pane
            pane.sync()

        # Tabify the dock widgets for better organization
        for dw in dws:
            if dw == dws[0]:
                continue
            self.tabifyDockWidget(dws[0], dw)

        # Raise the first dock widget to the top
        dws[0].raise_()

        # Update the window title to reflect the current project
        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")

    def connect_signals(self):
        # Keyboard shortcuts
        signals.project.changed.connect(self.sync)

    def clearPanes(self):
        for pane in self.panes():
            pane.deleteLater()

    def panes(self):
        """
        Return a list of all panes in the main window.
        """
        from activity_browser.ui import widgets
        return self.findChildren(widgets.ABAbstractPane)

    def set_titlebar(self):
        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")

    def dialog_on_exception(self, exception: Exception):
        QtWidgets.QMessageBox.critical(
            self,
            f"An error occurred: {type(exception).__name__}",
            f"An error occurred, check the logs for more information \n\n {str(exception)}",
            QtWidgets.QMessageBox.Ok,
        )
