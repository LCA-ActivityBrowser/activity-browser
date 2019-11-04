# -*- coding: utf-8 -*-
import json

import brightway2 as bw
from PySide2 import QtCore, QtWidgets, QtGui

from .icons import qicons
from ..signals import signals
from .widgets import BiosphereUpdater
from .wizards.settings_wizard import SettingsWizard


class MenuBar(object):
    def __init__(self, window):
        self.window = window
        self.update_biosphere_action = QtWidgets.QAction("&Update biosphere...")
        self.biosphere_updater = None

        self.menubar = QtWidgets.QMenuBar()
        self.menubar.addMenu(self.setup_file_menu())
        # self.menubar.addMenu(self.setup_tools_menu())
        # self.menubar.addMenu(self.setup_extensions_menu())
        self.menubar.addMenu(self.setup_view_menu())
        self.menubar.addMenu(self.setup_windows_menu())
        self.menubar.addMenu(self.setup_help_menu())
        window.setMenuBar(self.menubar)
        self.connect_signals()

    def connect_signals(self):
        signals.update_windows.connect(self.update_windows_menu)
        signals.project_selected.connect(self.biosphere_exists)
        signals.databases_changed.connect(self.biosphere_exists)
        self.update_biosphere_action.triggered.connect(self.update_biosphere)

    # FILE
    def setup_file_menu(self):
        menu = QtWidgets.QMenu('&File', self.window)
        menu.addAction(
            qicons.import_db,
            '&Import database...',
            signals.import_database.emit
        )
        menu.addAction(self.update_biosphere_action)
        menu.addAction(
            qicons.settings,
            '&Settings...',
            self.open_settings_wizard
        )
        return menu

    # VIEW
    def setup_view_menu(self):
        view_menu = QtWidgets.QMenu('&View', self.window)
        view_menu.addAction(
            qicons.graph_explorer,
            '&Graph Explorer',
            lambda x="Graph Explorer": signals.toggle_show_or_hide_tab.emit(x)
        )
        view_menu.addAction(
            qicons.history,
            '&Activity History',
            lambda x="History": signals.toggle_show_or_hide_tab.emit(x)
        )
        view_menu.addAction(
            qicons.welcome,
            '&Welcome screen',
            lambda x="Welcome": signals.toggle_show_or_hide_tab.emit(x)
        )
        return view_menu

    # WINDOWS
    def setup_windows_menu(self):
        self.windows_menu = QtWidgets.QMenu('&Windows', self.window)
        self.update_windows_menu()
        return self.windows_menu

    def update_windows_menu(self):
        self.windows_menu.clear()
        for index in range(self.window.stacked.count()):  # iterate over widgets in QStackedWidget
            widget = self.window.stacked.widget(index)
            self.windows_menu.addAction(
                widget.icon,
                widget.name,
                lambda widget=widget: self.window.stacked.setCurrentWidget(widget),
            )

    # HELP
    def setup_help_menu(self):
        help_menu = QtWidgets.QMenu('&Help', self.window)
        help_menu.addAction(
            self.window.icon,
            '&About Activity Browser',
            self.about)
        help_menu.addAction(
            '&About Qt',
            lambda: QtWidgets.QMessageBox.aboutQt(self.window)
        )
        help_menu.addAction(
            qicons.issue,
            '&Report an idea/issue on GitHub',
            self.raise_issue_github
        )

        return help_menu

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
        QtGui.QDesktopServices.openUrl(url)

    def open_settings_wizard(self):
        self.settings_wizard = SettingsWizard()

    def biosphere_exists(self) -> None:
        """ Test if the default biosphere exists as a database in the project
        """
        exists = True if bw.config.biosphere in bw.databases else False
        self.update_biosphere_action.setEnabled(exists)

    def update_biosphere(self):
        """ Open a popup with progression bar and run through the different
        functions for adding ecoinvent biosphere flows.
        """
        self.biosphere_updater = BiosphereUpdater()
