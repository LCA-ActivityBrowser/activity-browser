# -*- coding: utf-8 -*-
import os
from pathlib import Path

from PySide2 import QtCore, QtGui, QtWebEngineWidgets, QtWidgets

# type "localhost:3999" in Chrome for DevTools of AB web content
from activity_browser.i18n import current_language
from activity_browser.utils import get_base_path

os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "3999"


class RestrictedQWebEnginePage(QtWebEngineWidgets.QWebEnginePage):
    """Filters links so that users cannot just navigate to any page on the web,
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
            html_file = localized_html_path(html_file)
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


def get_static_js_path(file_name: str = "") -> str:
    return str(get_base_path().joinpath("static", "javascript", file_name))


def get_static_css_path(file_name: str = "") -> str:
    return str(get_base_path().joinpath("static", "css", file_name))


def localized_html_path(html_file: str, language: str = None) -> str:
    """Return a language-specific sibling HTML file when one exists.

    For example, ``welcome.html`` resolves to ``welcome.zh_CN.html`` when the
    current language is Simplified Chinese.  Missing translations safely fall
    back to the original file.
    """

    path = Path(html_file)
    language = language or current_language()
    localized = path.with_name(f"{path.stem}.{language}{path.suffix}")
    return str(localized if localized.is_file() else path)
