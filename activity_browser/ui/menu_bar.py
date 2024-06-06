from PySide2 import QtWidgets, QtGui
from PySide2.QtCore import QSize, QUrl, Slot

from activity_browser import actions, signals
from activity_browser.mod import bw2data as bd

from ..info import __version__ as ab_version
from .icons import qicons


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.window = window
        self.file_menu = QtWidgets.QMenu('&File', self.window)
        self.view_menu = QtWidgets.QMenu('&View', self.window)
        self.windows_menu = QtWidgets.QMenu('&Windows', self.window)
        self.tools_menu = QtWidgets.QMenu('&Tools', self.window)
        self.help_menu = QtWidgets.QMenu('&Help', self.window)

        self.update_biosphere_action = actions.BiosphereUpdate.get_QAction()
        self.export_db_action = actions.DatabaseExport.get_QAction()
        self.import_db_action = actions.DatabaseImport.get_QAction()
        self.manage_plugins_action = actions.PluginWizardOpen.get_QAction()
        self.manage_settings_action = actions.SettingsWizardOpen.get_QAction()

        self.addMenu(self.file_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.tools_menu)
        self.addMenu(self.help_menu)

        self.setup_file_menu()
        self.setup_view_menu()
        self.setup_tools_menu()
        self.setup_help_menu()
        self.connect_signals()

    def connect_signals(self):
        bd.projects.current_changed.connect(self.biosphere_exists)
        bd.databases.metadata_changed.connect(self.biosphere_exists)

    def setup_file_menu(self) -> None:
        """Build the menu for specific importing/export/updating actions."""
        self.file_menu.addAction(self.import_db_action)
        self.file_menu.addAction(self.export_db_action)
        self.file_menu.addAction(self.update_biosphere_action)
        self.file_menu.addAction(self.manage_settings_action)

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
For copyright information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/tree/main#copyright">this page</a>.<br><br>
For license information please see the copyright on <a href="https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/LICENSE.txt">this page</a>.<br><br>
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
        exists = True if bd.config.biosphere in bd.databases else False
        self.update_biosphere_action.setEnabled(exists)
        self.import_db_action.setEnabled(exists)

