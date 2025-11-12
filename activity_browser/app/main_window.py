from pathlib import Path
from loguru import logger

from qtpy import QtCore, QtWidgets, QtGui

import bw2data as bd
from activity_browser import app
from activity_browser.ui import widgets


class MainWindow(QtWidgets.QMainWindow):
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    

    def __init__(self, parent=None):
        from activity_browser.app.menu_bar import MenuBar

        if self._initialized:
            return
        self._initialized = True
        
        super().__init__(parent)

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Activity Browser")
        self.setDockNestingEnabled(True)

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.central_widget = widgets.CentralTabWidget(self)
        self.setCentralWidget(self.central_widget)

        self.connect_signals()

    def sync(self):
        self.sync_panes()
        self.sync_pages()

        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")
    
    def sync_panes(self):
        self.clearPanes()

        dws = []

        # Iterate through the default panes and add them as dock widgets
        for pane_name, pane_class in app.panes.base_panes.items():
            pane = pane_class(parent=self)
            dockwidget = pane.getDockWidget(self)
            dws.append(dockwidget)

            # Add the dock widget to the left dock area
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockwidget)
            # Add the toggle view action to the menu bar
            self.menu_bar.view_menu.addAction(dockwidget.toggleViewAction())

            # Hide the dock widget if it is marked as hidden
            if pane_name not in app.settings["startup"]["shown_panes"]:
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
    
    def sync_pages(self):
        """
        Synchronizes the central widget pages with the shown_pages setting.
        
        This method clears existing pages and adds only those pages that are
        configured to be shown at startup.
        """
        # Clear existing pages
        while self.central_widget.count() > 0:
            self.central_widget.removeTab(0)
        
        # Add pages based on shown_pages setting
        shown_pages = app.settings["startup"].get("shown_pages", [])
        
        for page_name in shown_pages:
            if page_name in app.pages.base_pages:
                page_class = app.pages.base_pages[page_name]
                page_instance = page_class()
                self.central_widget.addTab(page_instance, page_name)

    def apply_settings(self, load=False):

        base_dir = Path(app.settings["startup"]["brightway_directory"])

        if load or base_dir != bd.projects._base_data_dir:
            project_name = app.settings["startup"]["startup_project"]
            bd.projects.change_base_directories(base_dir, project_name=project_name, update=False)

            if not bd.projects.twofive:
                logger.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
                app.actions.ProjectSwitch.set_warning_bar()
        
        # Apply appearance settings
        if app.settings["appearance"]["theme"] == "dark":
            hint = QtCore.Qt.ColorScheme.Dark
        elif app.settings["appearance"]["theme"] == "light":
            hint = QtCore.Qt.ColorScheme.Light
        else:
            hint = QtCore.Qt.ColorScheme.Unknown
        
        app.application.styleHints().setColorScheme(hint)

    def connect_signals(self):
        app.signals.project.changed.connect(self.sync)
        app.signals.settings.changed.connect(self.apply_settings)

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

