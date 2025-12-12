from pathlib import Path
from loguru import logger

from qtpy import QtCore, QtWidgets

import bw2data as bd
from activity_browser import app
from activity_browser.ui import widgets


class MainWindow(widgets.ABMainWindow):

    def __init__(self, parent=None):
        from activity_browser.app.menu_bar import MenuBar
        super().__init__(parent)

        self.setWindowTitle("Activity Browser")

        # Layout: extra items outside main layout
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.central_widget = widgets.ABCentralPagesWidget(self)
        self.setCentralWidget(self.central_widget)

        for page_name, page_class in app.pages.base_pages.items():
            page_instance = page_class(parent=self.central_widget)
            self.central_widget.addPage(page_instance)
            self.menu_bar.view_menu.addAction(page_instance.toggleViewAction())

        self.menu_bar.view_menu.addSeparator()

        self.connect_signals()

    def connect_signals(self):
        app.signals.project.changed.connect(self.sync)
        app.signals.settings.changed.connect(self.apply_settings)

    def sync(self):
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")
        self.sync_panes()
        self.sync_pages()

        self.setWindowTitle(f"Activity Browser - {bd.projects.current}")
        self.central_widget.setCurrentIndex(0)
    
    def sync_panes(self):
        self.clearPanes()

        # Iterate through the base panes and add them
        for pane_name, pane_class in app.panes.base_panes.items():
            pane = pane_class(parent=self)
            self.addPane(pane)

            self.menu_bar.view_menu.addAction(pane.toggleViewAction())

            # Hide the dock widget if it is marked as hidden
            if pane_name not in app.settings["startup"]["shown_panes"]:
                pane.hide()

        # Tabify the dock widgets for better organization
        dws = [pane.getDockWidget() for pane in self.panes()]
        for dw in dws:
            if dw == dws[0]:
                continue
            self.tabifyDockWidget(dws[0], dw)

        # Raise the first dock widget to the top
        dws[0].raise_()
    
    def sync_pages(self):
        """
        Synchronizes the central widget pages with the shown_pages setting.

        This method shows only those pages that are configured to be shown at startup.
        Pages are pre-initialized and just added/removed from tabs.
        """
        # Get shown pages from settings
        shown_pages = app.settings["startup"].get("shown_pages", [])

        # Remove all pages from tabs first
        for i in range(self.central_widget.count()):
            self.central_widget.closeTab(0)

        # Add only the pages that should be shown
        for page_name in shown_pages:
            if page_name in app.pages.base_pages:
                page = self.findChild(app.pages.base_pages[page_name])
                if page:
                    self.central_widget.addPage(page)

    def apply_settings(self, load=False):

        base_dir = Path(app.settings["startup"]["brightway_directory"])

        if load or base_dir != bd.projects._base_data_dir:
            project_name = app.settings["startup"]["startup_project"]
            bd.projects.change_base_directories(base_dir, project_name=project_name, update=False)

            if not bd.projects.twofive:
                logger.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
                app.actions.ProjectSwitch.set_warning_bar()
        
        # Apply color scheme settings
        if app.settings["appearance"]["theme"] == "dark":
            hint = QtCore.Qt.ColorScheme.Dark
        elif app.settings["appearance"]["theme"] == "light":
            hint = QtCore.Qt.ColorScheme.Light
        else:
            hint = QtCore.Qt.ColorScheme.Unknown
        
        app.application.styleHints().setColorScheme(hint)

        # apply pane tab position
        position = app.settings["appearance"]["pane_tab_position"]
        if position == "top":
            qt_position = QtWidgets.QTabWidget.TabPosition.North
        if position == "bottom":
            qt_position = QtWidgets.QTabWidget.TabPosition.South
        if position == "left":
            qt_position = QtWidgets.QTabWidget.TabPosition.West
        if position == "right":
            qt_position = QtWidgets.QTabWidget.TabPosition.East
        self.setTabPosition(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas, qt_position)

    def dialog_on_exception(self, exception: Exception):
        QtWidgets.QMessageBox.critical(
            self,
            f"An error occurred: {type(exception).__name__}",
            f"An error occurred, check the logs for more information \n\n {str(exception)}",
            QtWidgets.QMessageBox.Ok,
        )

