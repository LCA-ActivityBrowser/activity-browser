import os

from qtpy import QtWebEngineWidgets, QtWidgets, QtCore, QtGui

from activity_browser.static import startscreen


class WelcomePage(QtWidgets.QWidget):
    html_file = os.path.join(startscreen.__path__[0], "welcome.html")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.page = WelcomeWebPage()

        self.url = QtCore.QUrl.fromLocalFile(self.html_file)
        self.page.allowed_pages.append(self.url)
        self.page.load(self.url)

        # associate page with view
        self.view.setPage(self.page)

        # set layout
        self.vl = QtWidgets.QVBoxLayout()
        self.vl.addWidget(self.view)
        self.setLayout(self.vl)


class WelcomeWebPage(QtWebEngineWidgets.QWebEnginePage):
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
