# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtCore, QtWebEngineWidgets


class SimpleWebPageWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, html_file=None, url=None):
        super().__init__(parent)
        if html_file:
            self.url = QtCore.QUrl.fromLocalFile(html_file)
        elif url:
            pass  # we don't want to display websites at this moment, but the code below would work
            # self.url = QtCore.QUrl(url)

        if self.url:
            # create view
            self.view = QtWebEngineWidgets.QWebEngineView()
            self.view.load(self.url)
            # set layout
            self.vl = QtWidgets.QVBoxLayout()
            self.vl.addWidget(self.view)
            self.setLayout(self.vl)
