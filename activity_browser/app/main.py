from pathlib import Path
from loguru import logger

from qtpy import QtCore, QtWidgets

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
        self.central_widget.setTabsClosable(True)
        self.setCentralWidget(self.central_widget)
        
        # Initialize all base pages upfront (name -> widget instance)
        self.base_pages = {}
        for page_name, page_class in app.pages.base_pages.items():
            page_instance = page_class()
            page_instance.setObjectName(page_name)
            self.base_pages[page_name] = page_instance
        
        # Connect tab close signal
        self.central_widget.tabCloseRequested.connect(self._on_tab_close_requested)

        self.connect_signals()
        self.destroyed.connect(lambda: logger.warning("MainWindow destroyed"))

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
            for page in self.base_pages.values():
                logger.debug(f"Destroying base page {page.__class__.__name__}: {id(page)}")
                try:
                    page.deleteLater()
                except RuntimeError:
                    # page already deleted
                    pass
        return super().event(event)

    def sync(self):
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")
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
        
        This method shows only those pages that are configured to be shown at startup.
        Pages are pre-initialized and just added/removed from tabs.
        """
        # Get shown pages from settings
        shown_pages = app.settings["startup"].get("shown_pages", [])
        
        # Remove all pages from tabs first
        while self.central_widget.count() > 0:
            self.central_widget.removeTab(0)
        
        # Add only the pages that should be shown
        for page_name in shown_pages:
            if page_name in self.base_pages:
                page_instance = self.base_pages[page_name]
                # Base pages should show minimize button instead of close
                self.central_widget.addTab(page_instance, page_name, show_minimize=True)
    
    def show_page(self, page_name: str):
        """
        Show a page by adding it to the tabs.
        
        Args:
            page_name: The name of the page to show
        """
        if page_name not in self.base_pages:
            return
        
        page_widget = self.base_pages[page_name]
        
        # Check if page is already in tabs
        index = self.central_widget.indexOf(page_widget)
        if index >= 0:
            # Already shown, just switch to it
            self.central_widget.setCurrentIndex(index)
        else:
            # Add to tabs with minimize button
            self.central_widget.addTab(page_widget, page_name, show_minimize=True)
            self.central_widget.setCurrentWidget(page_widget)
    
    def hide_page(self, page_name: str):
        """
        Hide a page by removing it from the tabs (but not destroying it).
        
        Args:
            page_name: The name of the page to hide
        """
        if page_name not in self.base_pages:
            return
        
        page_widget = self.base_pages[page_name]
        index = self.central_widget.indexOf(page_widget)
        if index >= 0:
            self.central_widget.removeTab(index)
    
    def toggle_page(self, page_name: str):
        """
        Toggle a page shown/hidden.
        
        Args:
            page_name: The name of the page to toggle
        """
        if page_name not in self.base_pages:
            return
        
        page_widget = self.base_pages[page_name]
        index = self.central_widget.indexOf(page_widget)
        
        if index >= 0:
            # Page is shown, hide it
            self.hide_page(page_name)
        else:
            # Page is hidden, show it
            self.show_page(page_name)
    
    def is_page_visible(self, page_name: str) -> bool:
        """
        Check if a page is currently visible in the tabs.
        
        Args:
            page_name: The name of the page to check
            
        Returns:
            bool: True if the page is visible, False otherwise
        """
        if page_name not in self.base_pages:
            return False
        
        page_widget = self.base_pages[page_name]
        return self.central_widget.indexOf(page_widget) >= 0
    
    def _on_tab_close_requested(self, index: int):
        """
        Handle when user clicks the close button on a tab.
        For base pages, we just hide them instead of destroying them.
        
        Args:
            index: The index of the tab to close
        """
        widget = self.central_widget.widget(index)
        if widget is None:
            return
        
        # Check if this is a base page
        page_name = widget.objectName()
        if page_name in self.base_pages:
            # Just remove from tabs, don't destroy
            self.central_widget.removeTab(index)
        else:
            # For non-base pages, remove and destroy
            self.central_widget.removeTab(index)
            widget.deleteLater()

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
            qt_position = QtWidgets.QTabWidget.North
        if position == "bottom":
            qt_position = QtWidgets.QTabWidget.South
        if position == "left":
            qt_position = QtWidgets.QTabWidget.West
        if position == "right":
            qt_position = QtWidgets.QTabWidget.East
        self.setTabPosition(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas, qt_position)

    def connect_signals(self):
        app.signals.project.changed.connect(self.sync)
        app.signals.settings.changed.connect(self.apply_settings)

    def clearPanes(self):
        for pane in self.panes():
            logger.debug(f"Clearing pane {pane.__class__.__name__}: {id(pane)}")
            pane.deleteLater()

    def panes(self):
        """
        Return a list of all panes in the main window.
        """
        from activity_browser.ui import widgets
        QtWidgets.QApplication.processEvents()
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

