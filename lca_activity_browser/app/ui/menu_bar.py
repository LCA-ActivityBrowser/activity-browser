# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class MenuBar(object):
    def __init__(self, window):
        self.window = window
        self.menubar = QtWidgets.QMenuBar()
        self.menubar.addMenu(self.get_extensions_menu())
        self.menubar.addMenu(self.get_help_menu())
        window.setMenuBar(self.menubar)

    def get_extensions_menu(self):
        extensions_menu = QtWidgets.QMenu('&Extensions', self.window)
        # extensions_menu.addAction(
        #     self.add_metaprocess_menu_item()
        # )
        return extensions_menu

    def get_help_menu(self):
        help_menu = QtWidgets.QMenu('&Help', self.window)
        help_menu.addAction(
            self.window.icon,
            '&About Activity Browser',
            self.about)
        help_menu.addAction(
            '&About Qt',
            lambda x: QtWidgets.QMessageBox.aboutQt(self.window)
        )
        return help_menu

    def about(self):
        text = """
Activity Browser - a graphical interface for Brightway2.

Copyright (c) 2015, Bernhard Steubing and ETH Zurich
Copyright (c) 2016, Chris Mutel and Paul Scherrer Institut
Contact: cmutel@gmail.com

LICENSE:
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>."""
        msgBox = QtWidgets.QMessageBox()
        # msgBox.setMinimumSize(QtCore.QSize(400, 400))
        msgBox.setWindowTitle('About the Activity Browser')
        pixmap = self.window.icon.pixmap(QtCore.QSize(150, 150))
        msgBox.setIconPixmap(pixmap)
        msgBox.setWindowIcon(self.window.icon)
        msgBox.setText(text)
        msgBox.setFixedSize(QtCore.QSize(400, 400))
        msgBox.exec_()
