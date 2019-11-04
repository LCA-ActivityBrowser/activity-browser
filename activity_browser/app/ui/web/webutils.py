# -*- coding: utf-8 -*-
from PySide2 import QtWidgets, QtCore, QtGui, QtWebEngineWidgets
import os


# type "localhost:3999" in Chrome for DevTools of AB web content
os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = '3999'


class RestrictedQWebEnginePage(QtWebEngineWidgets.QWebEnginePage):
    """ Filters links so that users cannot just navigate to any page on the web,
    but just to those pages, that are listed in allowed_pages.
    This is achieved by re-implementing acceptNavigationRequest.
    The latter could also be adapted to accept, e.g. URLs within a domain.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.allowed_pages = []

    def acceptNavigationRequest(self, qurl, navtype, mainframe):
        # print("Navigation Request intercepted:", qurl)
        if qurl in self.allowed_pages:  # open in Activity Browser QWebEngineView
            return True
        else:  # delegate link to default browser
            QtGui.QDesktopServices.openUrl(qurl)
            return False


class RestrictedWebViewWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, url=None, html_file=None):
        super().__init__(parent)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.page = RestrictedQWebEnginePage()

        if html_file:
            # print("Loading File:", html_file)
            self.url = QtCore.QUrl.fromLocalFile(html_file)
            self.page.allowed_pages.append(self.url)
            self.page.load(self.url)
        elif url:
            # print("Loading URL:", url)
            self.url = QtCore.QUrl(url)
            self.page.allowed_pages.append(self.url)
            self.page.load(self.url)

        # associate page with view
        self.view.setPage(self.page)


        # set layout
        self.vl = QtWidgets.QVBoxLayout()
        self.vl.addWidget(self.view)
        self.setLayout(self.vl)