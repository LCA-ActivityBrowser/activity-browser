import os

from qtpy import QtWebEngineWidgets, QtWidgets, QtCore, QtGui, QtWebChannel

from activity_browser import app
from activity_browser.ui import widgets
from activity_browser.static import startscreen
from activity_browser.bwutils.commontasks import projects_by_last_opened


class WelcomePage(widgets.ABAbstractPage):
    basePage = True
    title = "Welcome"

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
        self.page.load(self.url)

        # associate page with view
        self.view.setPage(self.page)

        # set layout
        self.vl = QtWidgets.QVBoxLayout()
        self.vl.addWidget(self.view)
        self.setLayout(self.vl)

        self.bridge.ready.connect(self.update_welcome)
        app.application.theme_changed.connect(self._reload_page)
        app.signals.project.changed.connect(self._reload_page)
        self.page.loadFinished.connect(self._on_load_finished)

    def _reload_page(self, *_args) -> None:
        self.page.load(self.url)

    def _on_load_finished(self, ok: bool) -> None:
        if not ok:
            return
        scheme = (
            "dark"
            if app.application.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark
            else "light"
        )
        self.page.runJavaScript(
            f'document.documentElement.style.colorScheme = "{scheme}";'
        )

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
        app.actions.ProjectSwitch.run(project_name)

class WelcomeWebPage(QtWebEngineWidgets.QWebEnginePage):
    def acceptNavigationRequest(self, qurl, navtype, mainframe):
        # print("Navigation Request intercepted:", qurl)
        if qurl.isLocalFile():  # open in Activity Browser QWebEngineView
            return True
        else:  # delegate link to default browser
            QtGui.QDesktopServices.openUrl(qurl)
            return False
