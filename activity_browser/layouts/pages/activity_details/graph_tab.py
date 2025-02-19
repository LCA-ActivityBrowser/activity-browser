import json
import os
from logging import getLogger

from qtpy import QtWebChannel, QtWebEngineWidgets, QtWidgets
from qtpy.QtCore import QObject, Qt, QUrl, Signal, SignalInstance, Slot

from activity_browser import static

log = getLogger(__name__)

test_json = """
{
    "nodes": [
        {
            "id": "choc_proc",
            "name": "Chocolate Factory",
            "functions": [
                {
                    "name": "Chocolate",
                    "id": "chocolate"
                }
            ]
        },
        {
            "id": "elec_proc",
            "name": "Combined Heat & Power",
            "location": "NL",
            "functions": [
                {
                    "name": "Electricity",
                    "id": "electricity"
                },
                {
                    "name": "Heat",
                    "id": "heat"
                }
            ]
        },
        {
            "id": "beans_proc",
            "name": "Chocolate Beans Market",
            "functions": [
                {
                    "name": "Chocolate Beans",
                    "id": "chocolate_beans"
                }
            ]
        }
    ],
    "edges": [
        {
            "source_id": "elec_proc",
            "target_id": "choc_proc",
            "amount": 0.25,
            "unit": "kilowatt hour",
            "product": "Electricity",
            "product_id": "electricity"
        },
        {
            "source_id": "beans_proc",
            "target_id": "choc_proc",
            "amount": 0.00612146666666667,
            "unit": "kilogram",
            "product_id": "chocolate_beans"
        }
    ],
    "title": "transport, passenger car, electric"
}
"""


class GraphTab(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.button = QtWidgets.QPushButton("CLICK ME")
        self.button.clicked.connect(self.on_load_finish)

        self.bridge = Bridge(self)
        self.url = QUrl.fromLocalFile(os.path.join(static.__path__[0], "activity_graph.html"))

        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)

        self.page = Page()
        self.page.setWebChannel(self.channel)

        self.view = QtWebEngineWidgets.QWebEngineView(self)
        self.view.setContextMenuPolicy(Qt.PreventContextMenu)
        self.view.setPage(self.page)
        self.view.setUrl(self.url)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.bridge.ready.connect(self.on_load_finish)

    def on_load_finish(self):
        self.bridge.update_graph.emit(test_json)




class Bridge(QObject):
    update_graph: SignalInstance = Signal(str)
    ready: SignalInstance = Signal()

    @Slot()
    def is_ready(self):
        self.ready.emit()


class Page(QtWebEngineWidgets.QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QtWebEngineWidgets.QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: str, _: str):
        if level == QtWebEngineWidgets.QWebEnginePage.InfoMessageLevel:
            log.info(f"JS Info (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.WarningMessageLevel:
            log.warning(f"JS Warning (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.ErrorMessageLevel:
            log.error(f"JS Error (Line {line}): {message}")
        else:
            log.debug(f"JS Log (Line {line}): {message}")
