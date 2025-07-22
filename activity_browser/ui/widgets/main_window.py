import pickle
from logging import getLogger

from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals, settings
from activity_browser.ui import icons

from activity_browser.ui.menu_bar import MenuBar

log = getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setWindowIcon(icons.qicons.ab)
        self.setDockNestingEnabled(True)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.connect_signals()

    def closeEvent(self, event):
        """
        Save the state of the main window when it is closed.
        """
        # Save the state of the main window
        self.writeState(bd.projects.dir)
        super().closeEvent(event)

    def sync(self):
        from activity_browser.layouts import panes

        self.clearPanes()

        data = self.getState(bd.projects.dir)

        unique_panes = [pane for pane in panes.registered_panes if pane.unique]

        for pane_state in data.get("panes", []):
            self.restorePane(pane_state)
            if pane_state.get("class") in unique_panes:
                unique_panes.remove(pane_state.get("class"))

        for pane in unique_panes:
            self.addPane(pane(parent=self))

        success = self.restoreState(data.get("state"), 0)
        log.debug(f"Restored main window state: {success}")

        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")


    def connect_signals(self):
        # Keyboard shortcuts
        signals.project.changed.connect(self.on_project_changed)

    def clearPanes(self):
        for pane in self.panes():
            pane.deleteLater()

    def panes(self):
        """
        Return a list of all panes in the main window.
        """
        from activity_browser.ui import widgets
        return self.findChildren(widgets.ABAbstractPane)

    def on_project_changed(self, new, old):
        self.writeState(old.dir)
        self.sync()

    def restorePane(self, pane_state: dict):
        """
        Restore a pane in the main window based on its saved state.

        Args:
            pane_state (dict): A dictionary containing the class and state of the pane to restore.
                - "class": The class of the pane to be restored.
                - "state": The saved state of the pane.

        Returns:
            None
        """
        pane_class = pane_state.get("class")
        if pane_class is None:
            return

        log.debug(f"Restoring pane {pane_class.__name__}")

        try:
            # Attempt to create an instance of the pane using its saved state
            pane_instance = pane_class.fromState(pane_state.get("state"), self)
        except Exception as e:
            # Log an error if the pane cannot be restored
            log.error(f"Error restoring pane {pane_class.__name__}: {e}")
            return

        self.addPane(pane_instance)

    def addPane(self, pane: QtWidgets.QWidget):
        """
        Add a pane to the main window.

        Args:
            pane (QtWidgets.QWidget): The pane to add.

        Returns:
            None
        """
        dockwidget = pane.getDockWidget(self)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockwidget)
        self.menu_bar.view_menu.addAction(dockwidget.toggleViewAction())

        pane.sync()

    def writeState(self, directory):
        if not directory.exists():
            # project directory does not exist, may be temporary or because the project was deleted
            log.debug(f"Project directory {directory} does not exist, skipping state save.")
            return

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

    def getState(self, directory) -> dict:
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
            }
        return data


    def set_titlebar(self):
        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")

    def dialog_on_exception(self, exception: Exception):
        QtWidgets.QMessageBox.critical(
            self,
            f"An error occurred: {type(exception).__name__}",
            f"An error occurred, check the logs for more information \n\n {str(exception)}",
            QtWidgets.QMessageBox.Ok,
        )
