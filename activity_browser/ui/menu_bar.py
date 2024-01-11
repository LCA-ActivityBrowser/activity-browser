# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtWidgets, QtGui
from PySide2.QtCore import QSize, QUrl, Slot

from ..info import __version__ as ab_version
from .icons import qicons
from ..signals import signals


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.window = window
        self.file_menu = QtWidgets.QMenu('&File', self.window)
        self.view_menu = QtWidgets.QMenu('&View', self.window)
        self.windows_menu = QtWidgets.QMenu('&Windows', self.window)
        self.tools_menu = QtWidgets.QMenu('&Tools', self.window)
        self.help_menu = QtWidgets.QMenu('&Help', self.window)

        self.update_biosphere_action = QtWidgets.QAction(
            window.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload),
            "&Update biosphere...", None
        )
        self.export_db_action = QtWidgets.QAction(
            self.window.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon),
            "&Export database...", None
        )
        self.import_db_action = QtWidgets.QAction(
            qicons.import_db, '&Import database...', None
        )
        self.manage_plugins_action = QtWidgets.QAction(
            qicons.plugin, '&Plugins...', None
        )

        self.addMenu(self.file_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.windows_menu)
        self.addMenu(self.tools_menu)
        self.addMenu(self.help_menu)

        self.setup_file_menu()
        self.setup_view_menu()
        self.update_windows_menu()
        self.setup_tools_menu()
        self.setup_help_menu()
        self.connect_signals()

    def connect_signals(self):
        signals.update_windows.connect(self.update_windows_menu)
        signals.project_selected.connect(self.biosphere_exists)
        signals.databases_changed.connect(self.biosphere_exists)
        self.update_biosphere_action.triggered.connect(signals.update_biosphere.emit)
        self.export_db_action.triggered.connect(signals.export_database.emit)
        self.import_db_action.triggered.connect(signals.import_database.emit)
        self.manage_plugins_action.triggered.connect(signals.manage_plugins.emit)

    def setup_file_menu(self) -> None:
        """Build the menu for specific importing/export/updating actions."""
        self.file_menu.addAction(self.import_db_action)
        self.file_menu.addAction(self.export_db_action)
        self.file_menu.addAction(self.update_biosphere_action)
        self.file_menu.addAction(
            qicons.settings,
            '&Settings...',
            signals.edit_settings.emit
        )

    def setup_view_menu(self) -> None:
        """Build the menu for viewing or hiding specific tabs"""
        self.view_menu.addAction(
            qicons.graph_explorer,
            '&Graph Explorer',
            lambda: signals.toggle_show_or_hide_tab.emit("Graph Explorer")
        )
        self.view_menu.addAction(
            qicons.history,
            '&Activity History',
            lambda: signals.toggle_show_or_hide_tab.emit("History")
        )
        self.view_menu.addAction(
            qicons.welcome,
            '&Welcome screen',
            lambda: signals.toggle_show_or_hide_tab.emit("Welcome")
        )

    def update_windows_menu(self):
        """Clear and rebuild the menu for switching between tabs."""
        self.windows_menu.clear()
        for index in range(self.window.stacked.count()):  # iterate over widgets in QStackedWidget
            widget = self.window.stacked.widget(index)
            self.windows_menu.addAction(
                widget.icon,
                widget.name,
                self.window.toggle_debug_window,
            )

    def setup_tools_menu(self) -> None:
        """Build the tools menu for the menubar."""
        self.tools_menu.addAction(self.manage_plugins_action)
        
    def setup_help_menu(self) -> None:
        """Build the help menu for the menubar."""
        self.help_menu.addAction(
            self.window.icon,
            '&About Activity Browser',
            self.about)
        self.help_menu.addAction(
            '&About Qt',
            lambda: QtWidgets.QMessageBox.aboutQt(self.window)
        )
        self.help_menu.addAction(
            qicons.issue,
            '&Report an idea/issue on GitHub',
            self.raise_issue_github
        )

    def about(self):
        text = """
Activity Browser - a graphical interface for Brightway2.<br><br>
Application version: <b>{}</b><br><br>
All development happens on <a href="https://github.com/LCA-ActivityBrowser/activity-browser">github</a>.<br><br>
For copyright information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/tree/master#copyright">this page</a>.<br><br>
For license information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/master/LICENSE.txt">this page</a>.<br><br>
"""
        msgBox = QtWidgets.QMessageBox(parent=self.window)
        msgBox.setWindowTitle('About the Activity Browser')
        pixmap = self.window.icon.pixmap(QSize(150, 150))
        msgBox.setIconPixmap(pixmap)
        msgBox.setWindowIcon(self.window.icon)
        msgBox.setText(text.format(ab_version))
        msgBox.exec_()

    def raise_issue_github(self):
        url = QUrl('https://github.com/LCA-ActivityBrowser/activity-browser/issues/new/choose')
        QtGui.QDesktopServices.openUrl(url)

    @Slot(name="testBiosphereExists")
    def biosphere_exists(self) -> None:
        """ Test if the default biosphere exists as a database in the project
        """
        exists = True if bw.config.biosphere in bw.databases else False
        self.update_biosphere_action.setEnabled(exists)
        self.import_db_action.setEnabled(exists)
