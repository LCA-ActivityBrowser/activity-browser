import os

from qtpy import QtWebEngineWidgets, QtWidgets, QtCore, QtGui, QtWebChannel

from activity_browser import actions, signals
from activity_browser.static import startscreen
from activity_browser.bwutils import projects_by_last_opened


class WelcomePage(QtWidgets.QWidget):
    html_file = os.path.join(startscreen.__path__[0], "welcome.html")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.page = WelcomeWebPage()
        self.channel = QtWebChannel.QWebChannel(self)
        self.bridge = Bridge(self)
        self.channel.registerObject("bridge", self.bridge)

        self.url = QtCore.QUrl.fromLocalFile(self.html_file)
        self.page.setWebChannel(self.channel)
        self.page.allowed_pages.append(self.url)
        self.page.load(self.url)

        # associate page with view
        self.view.setPage(self.page)

        # set layout
        self.vl = QtWidgets.QVBoxLayout()
        self.vl.addWidget(self.view)
        self.setLayout(self.vl)

        self.bridge.ready.connect(self.update_welcome)
        signals.project.changed.connect(lambda: self.page.load(self.url))

    def update_welcome(self):
        projects = projects_by_last_opened()
        projects = projects[1:5] if len(projects) > 5 else projects[1:]
        project_names = [p.name for p in projects]
        self.bridge.update.emit(project_names)


class Bridge(QtCore.QObject):
    """
    A bridge for communication between Python and JavaScript.

    Attributes:
        update_graph (SignalInstance): A signal to update the graph.
        ready (SignalInstance): A signal indicating that the bridge is ready.
    """
    update: QtCore.SignalInstance = QtCore.Signal(list)
    ready: QtCore.SignalInstance = QtCore.Signal()

    @QtCore.Slot()
    def is_ready(self):
        """
        Emits the ready signal.
        """
        self.ready.emit()

    @QtCore.Slot(str)
    def open_project(self, project_name):
        """
        Emits the ready signal.
        """
        actions.ProjectSwitch.run(project_name)

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
