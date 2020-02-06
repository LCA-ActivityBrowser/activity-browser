# -*- coding: utf-8 -*-
from abc import abstractmethod
from copy import deepcopy
import json
import os
from typing import Type

from PySide2 import QtWebEngineWidgets, QtWebChannel, QtWidgets
from PySide2.QtCore import Signal, Slot, QObject, Qt, QUrl

from ...icons import qicons
from ....signals import signals


class BaseNavigatorWidget(QtWidgets.QWidget):
    HELP_TEXT = """
    This is the text shown when the user presses 'help'.
    """
    HTML_FILE = ""

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)

        # Graph object subclassed from BaseGraph.
        self.graph: Type[BaseGraph]

        # Setup JS / Qt interactions
        self.bridge = Bridge(self)
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.loadFinished.connect(self.load_finished_handler)
        self.view.setContextMenuPolicy(Qt.PreventContextMenu)
        self.view.page().setWebChannel(self.channel)
        self.url = QUrl.fromLocalFile(self.HTML_FILE)

        # Various Qt objects
        self.label_help = QtWidgets.QLabel(self.HELP_TEXT)
        self.button_toggle_help = QtWidgets.QPushButton("Help")
        self.button_back = QtWidgets.QPushButton(qicons.backward, "")
        self.button_forward = QtWidgets.QPushButton(qicons.forward, "")
        self.button_refresh = QtWidgets.QPushButton("Refresh HTML")
        self.button_random_activity = QtWidgets.QPushButton("Random Activity")

    def load_finished_handler(self, *args, **kwargs) -> None:
        """Executed when webpage has been loaded for the first time or refreshed.

        Can be used to trigger a calculation after the webpage has been
        completely loaded.
        """
        pass

    @abstractmethod
    def connect_signals(self) -> None:
        self.button_toggle_help.clicked.connect(self.toggle_help)
        self.button_back.clicked.connect(self.go_back)
        self.button_forward.clicked.connect(self.go_forward)
        self.button_refresh.clicked.connect(self.draw_graph)
        self.button_random_activity.clicked.connect(self.random_graph)

    @abstractmethod
    def construct_layout(self) -> None:
        pass

    def toggle_help(self) -> None:
        self.label_help.setVisible(self.label_help.isHidden())

    def go_forward(self) -> None:
        if self.graph.forward():
            signals.new_statusbar_message.emit("Going forward.")
            self.send_json()
        else:
            signals.new_statusbar_message.emit("No data to go forward to.")

    def go_back(self) -> None:
        if self.graph.back():
            signals.new_statusbar_message.emit("Going back.")
            self.send_json()
        else:
            signals.new_statusbar_message.emit("No data to go back to.")

    def send_json(self) -> None:
        self.bridge.graph_ready.emit(self.graph.json_data)

    def draw_graph(self) -> None:
        self.view.load(self.url)

    @abstractmethod
    def random_graph(self) -> None:
        pass


class Bridge(QObject):
    graph_ready = Signal(str)
    update_graph = Signal(object)

    @Slot(str, name="node_clicked")
    def node_clicked(self, click_text: str):
        """ Is called when a node is clicked in Javascript.
        Args:
            click_text: string of a serialized json dictionary describing
            - the node that was clicked on
            - mouse button and additional keys pressed
        """
        click_dict = json.loads(click_text)
        click_dict["key"] = (click_dict["database"], click_dict["id"])  # since JSON does not know tuples
        print("Click information: ", click_dict)
        self.update_graph.emit(click_dict)


class BaseGraph(object):
    def __init__(self):
        self.json_data = None
        # stores previous graphs, if any, and enables back/forward buttons
        self.stack = []
        # stores graphs that can be returned to after having used the "back" button
        self.forward_stack = []

    def update(self, delete_unstacked: bool = True) -> None:
        self.store_previous()
        if delete_unstacked:
            self.forward_stack = []

    def forward(self) -> bool:
        """Go forward, if previously gone back."""
        if not self.forward_stack:
            return False
        self.retrieve_future()
        self.update(delete_unstacked=False)
        return True

    def back(self) -> bool:
        """Go back to previous graph, if any."""
        if len(self.stack) <= 1:
            return False
        self.store_future()
        self.update(delete_unstacked=False)
        return True

    def store_previous(self) -> None:
        """Store the current graph in the """
        self.stack.append((deepcopy(self.json_data)))

    def store_future(self) -> None:
        """When going back, store current data in a queue."""
        self.forward_stack.append(self.stack.pop())
        self.json_data = self.stack.pop()

    def retrieve_future(self) -> None:
        """Extract the last graph from the queue."""
        self.json_data = self.forward_stack.pop()

    @abstractmethod
    def new_graph(self, *args, **kwargs) -> None:
        pass

    def save_json_to_file(self, filename: str = "graph_data.json") -> None:
        """ Writes the current model´s JSON representation to the specifies file. """
        if self.json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'w') as outfile:
                json.dump(self.json_data, outfile)
