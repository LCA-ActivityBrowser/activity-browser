# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore, QtGui, QtWebKit
from .icons import icons


class MenuBar(object):
    def __init__(self, window):
        self.window = window
        self.menubar = QtGui.QMenuBar()
        self.menubar.addMenu(self.get_extensions_menu())
        self.menubar.addMenu(self.get_help_menu())
        window.setMenuBar(self.menubar)

    def add_metaprocess_menu_item(self):
        add_metaprocess = QtGui.QAction(QtGui.QIcon(icons.metaprocess), '&Meta-Process Editor', self.window)
        add_metaprocess.setShortcut('Ctrl+E')
        add_metaprocess.setStatusTip('Start Meta-Process Editor')

        # add_metaprocess.triggered.connect(self.set_up_widgets_meta_process)

        return add_metaprocess

    def get_extensions_menu(self):
        extensions_menu = QtGui.QMenu('&Extensions', self.window)
        extensions_menu.addAction(
            self.add_metaprocess_menu_item()
        )
        return extensions_menu

    def get_help_menu(self):
        help_menu = QtGui.QMenu('&Help', self.window)
        help_menu.addAction(
            self.window.icon,
            '&About Activity Browser',
            self.about)
        help_menu.addAction(
            '&About Qt',
            lambda x: QtGui.QMessageBox.aboutQt(self.window)
        )
        return help_menu

    def about(self):
        text="""
Activity Browser - A free and extendable LCA software.

Copyright (c) 2015, Bernhard Steubing and ETH Zurich
Contact: steubing@ifu.baug.ethz.ch

Uses brightway2: http://brightwaylca.org/

LICENSE:
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>."""
        msgBox = QtGui.QMessageBox()
        # msgBox.setMinimumSize(QtCore.QSize(400, 400))
        msgBox.setWindowTitle('About the Activity Browser')
        pixmap = self.window.icon.pixmap(QtCore.QSize(150, 150))
        msgBox.setIconPixmap(pixmap)
        msgBox.setWindowIcon(self.window.icon)
        msgBox.setText(text)
        msgBox.setFixedSize(QtCore.QSize(400, 400))
        msgBox.exec_()
