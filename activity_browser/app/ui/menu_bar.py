# -*- coding: utf-8 -*-
import json

import brightway2 as bw
from PySide2 import QtCore, QtWidgets, QtGui

from .icons import qicons
from ..signals import signals
from .widgets import BiosphereUpdater
from .wizards.settings_wizard import SettingsWizard
from .wizards.db_export_wizard import DatabaseExportWizard


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, window):
        super().__init__(parent=window)
        self.window = window
        self.settings_wizard = None
        self.export_wizard = None
        self.biosphere_updater = None
        self.file_menu = QtWidgets.QMenu('&File', self.window)
        self.view_menu = QtWidgets.QMenu('&View', self.window)
        self.windows_menu = QtWidgets.QMenu('&Windows', self.window)
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

        self.addMenu(self.file_menu)
        self.addMenu(self.view_menu)
        self.addMenu(self.windows_menu)
        self.addMenu(self.help_menu)

        self.setup_file_menu()
        self.setup_view_menu()
        self.update_windows_menu()
        self.setup_help_menu()
        self.connect_signals()

    def connect_signals(self):
        signals.update_windows.connect(self.update_windows_menu)
        signals.project_selected.connect(self.biosphere_exists)
        signals.databases_changed.connect(self.biosphere_exists)
        self.update_biosphere_action.triggered.connect(self.update_biosphere)
        self.export_db_action.triggered.connect(self.transfer_database_wizard)
        self.import_db_action.triggered.connect(lambda: signals.import_database.emit(self.window))

    def setup_file_menu(self) -> None:
        """Build the menu for specific importing/export/updating actions."""
        self.file_menu.addAction(self.import_db_action)
        self.file_menu.addAction(self.export_db_action)
        self.file_menu.addAction(self.update_biosphere_action)
        self.file_menu.addAction(
            qicons.settings,
            '&Settings...',
            self.open_settings_wizard
        )

    def setup_view_menu(self) -> None:
        """Build the menu for viewing or hiding specific tabs"""
        self.view_menu.addAction(
            qicons.graph_explorer,
            '&Graph Explorer',
            lambda x="Graph Explorer": signals.toggle_show_or_hide_tab.emit(x)
        )
        self.view_menu.addAction(
            qicons.history,
            '&Activity History',
            lambda x="History": signals.toggle_show_or_hide_tab.emit(x)
        )
        self.view_menu.addAction(
            qicons.welcome,
            '&Welcome screen',
            lambda x="Welcome": signals.toggle_show_or_hide_tab.emit(x)
        )

    def update_windows_menu(self):
        """Clear and rebuild the menu for switching between tabs."""
        self.windows_menu.clear()
        for index in range(self.window.stacked.count()):  # iterate over widgets in QStackedWidget
            widget = self.window.stacked.widget(index)
            self.windows_menu.addAction(
                widget.icon,
                widget.name,
                lambda widget=widget: self.window.stacked.setCurrentWidget(widget),
            )

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
All development happens on <a href="https://github.com/LCA-ActivityBrowser/activity-browser">github</a>.<br><br>
Main developers:<br>
- Bernhard Steubing (CML Leiden University, b.steubing@cml.leidenuniv.nl)<br>
- Chris Mutel (Paul Scherer Institut, cmutel@gmail.com)<br>
- Adrian Haas (ETH Zurich, haasad@ethz.ch)<br>
- Daniel de Koning (CML Leiden University, d.g.de.koning@cml.leidenuniv.nl<br><br>
Copyright (c) 2015, Bernhard Steubing and ETH Zurich<br>
Copyright (c) 2016, Chris Mutel and Paul Scherrer Institut<br>
Copyright (c) 2017, Adrian Haas (ETH Zurich) and Bernhard Steubing (Leiden University)<br>
<br>
LICENSE:<br>
This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.<br><br>
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.<br><br>
You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see <a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.
"""
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowTitle('About the Activity Browser')
        pixmap = self.window.icon.pixmap(QtCore.QSize(150, 150))
        msgBox.setIconPixmap(pixmap)
        msgBox.setWindowIcon(self.window.icon)
        msgBox.setText(text)
        msgBox.exec_()

    def raise_issue_github(self):
        url = QtCore.QUrl('https://github.com/LCA-ActivityBrowser/activity-browser/issues/new')
        QtGui.QDesktopServices.openUrl(url=url)

    def open_settings_wizard(self):
        self.settings_wizard = SettingsWizard(self.window)

    def transfer_database_wizard(self) -> None:
        self.export_wizard = DatabaseExportWizard(self.window)

    def biosphere_exists(self) -> None:
        """ Test if the default biosphere exists as a database in the project
        """
        exists = True if bw.config.biosphere in bw.databases else False
        self.update_biosphere_action.setEnabled(exists)
        self.import_db_action.setEnabled(exists)

    def update_biosphere(self):
        """ Open a popup with progression bar and run through the different
        functions for adding ecoinvent biosphere flows.
        """
        ok = QtWidgets.QMessageBox.question(
            self.window, "Update biosphere3?",
            "Updating the biosphere3 database cannot be undone!",
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Abort,
            QtWidgets.QMessageBox.Abort
        )
        if ok == QtWidgets.QMessageBox.Ok:
            self.biosphere_updater = BiosphereUpdater(self.window)
