# -*- coding: utf-8 -*-
import json

import requests
from PyQt5 import QtCore, QtWidgets, QtGui

from .icons import icons
from .utils import abt1
from ..signals import signals


class MenuBar(object):
    def __init__(self, window):
        self.window = window
        self.menubar = QtWidgets.QMenuBar()
        self.menubar.addMenu(self.setup_file_menu())
        # self.menubar.addMenu(self.setup_extensions_menu())
        self.menubar.addMenu(self.setup_help_menu())
        window.setMenuBar(self.menubar)

    def setup_file_menu(self):
        menu = QtWidgets.QMenu('&File', self.window)
        # Switch BW2 directory
        # switch_bw2_dir = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Database directory...', self.window)
        # # switch_bw2_dir.setShortcut('Ctrl+Q')
        # switch_bw2_dir.setStatusTip('Change database directory')
        # switch_bw2_dir.triggered.connect(signals.switch_bw2_dir_path.emit)
        # menu.addAction(switch_bw2_dir)
        menu.addAction(
            '&Database directory...',
            signals.switch_bw2_dir_path.emit
        )
        menu.addAction(
            '&Import database...',
            signals.import_database.emit
        )
        return menu

    # def setup_extensions_menu(self):
    #     extensions_menu = QtWidgets.QMenu('&Extensions', self.window)
    #     # extensions_menu.addAction(
    #     #     self.add_metaprocess_menu_item()
    #     # )
    #     return extensions_menu

    def setup_help_menu(self):
        bug_icon = QtGui.QIcon(icons.debug)
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
            bug_icon,
            '&Report Bug on github',
            self.raise_issue_github
        )
        help_menu.addAction(
            bug_icon,
            '&Report Bug',
            self.raise_issue_from_app
        )
        return help_menu

    def about(self):
        text = '''
Activity Browser - a graphical interface for Brightway2.<br><br>
All development happens on <a href="https://github.com/LCA-ActivityBrowser/activity-browser">github</a>.<br><br>
Main developers:<br>
- Bernhard Steubing (CML Leiden University, b.steubing@cml.leidenuniv.nl)<br>
- Chris Mutel (Paul Scherer Institut, cmutel@gmail.com)<br>
- Adrian Haas (ETH Zurich, haasad@ethz.ch)<br><br>
Copyright (c) 2015, Bernhard Steubing and ETH Zurich<br>
Copyright (c) 2016, Chris Mutel and Paul Scherrer Institut<br>
Copyright (c) 2017, Adrian Haas (ETH Zurich) and Bernhard Steubing (Leiden University)<br>
<br>
LICENSE:<br>
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.<br><br>
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.<br><br>
You should have received a copy of the GNU General Public License along with this program.  If not, see <a href="http://www.gnu.org/licenses/">http://www.gnu.org/licenses/</a>.
'''
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

    def raise_issue_api(self, content):
        abt2 = 'C5F02AZ12E56E6D46Z811D'
        auth = (
            'ActivityBrowser',
            ''.join(reversed(abt1 + ''.join(reversed(abt2.lower())))).replace('z', '')
        )
        data = {
            'title': 'New issue reported from app',
            'body': content
        }

        url = 'https://api.github.com/repos/LCA-ActivityBrowser/activity-browser/issues'
        response = requests.post(url, data=json.dumps(data), auth=auth)
        if response.status_code != 201:
            print(response)
            print(response.text)

    def raise_issue_from_app(self):
        text, _ = QtWidgets.QInputDialog.getMultiLineText(
            None,
            'Report new bug',
            ('Please describe the buggy behaviour. View existing issues on ' +
             '<a href="https://github.com/LCA-ActivityBrowser/activity-browser/issues">github</a>.'+
             '<br>If you have a github account, please consider raising the issue directly on github.'
             ),
        )
        if text:
            content = text + '\n\nLog Output:\n```\n{}```'.format(self.window.log.toPlainText())
            self.raise_issue_api(content)
            print(content)
