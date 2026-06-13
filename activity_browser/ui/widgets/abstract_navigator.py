import json
import os
from abc import abstractmethod
from copy import deepcopy
from typing import Type
from loguru import logger

from qtpy import QtWebChannel, QtWebEngineWidgets, QtWidgets
from qtpy.QtCore import QObject, Qt, QUrl, Signal, Slot

from activity_browser.ui.icons import qicons
from activity_browser.bwutils import filesystem

from .web_engine_page import ABWebEnginePage


class ABAbstractNavigator(QtWidgets.QWidget):
    HELP_TEXT = """
    This is the text shown when the user presses 'help'.
    """
    HTML_FILE = ""

    def __init__(self, parent=None, css_file: str = "", *args, **kwargs):
        super().__init__(parent)

        # Graph object subclassed from BaseGraph.
        self.graph: Type[ABAbstractGraph]

        # Setup JS / Qt interactions
        self.bridge = Bridge(self)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView(self)
        self.page = ABWebEnginePage(self.view)
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self.load_finished_handler)
        self.view.setContextMenuPolicy(Qt.PreventContextMenu)
        self.view.page().setWebChannel(self.channel)
        self.url = QUrl.fromLocalFile(self.HTML_FILE)
        self.css_file = css_file
        self.plot_name = "Figure"

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
            self.send_json()

    def go_back(self) -> None:
        if self.graph.back():
            self.send_json()

    def send_json(self) -> None:
        if self.graph.json_data is None:
            return
        self.bridge.graph_ready.emit(self.graph.json_data)
        css_path = get_static_css_path(self.css_file)

        with open(css_path, "r") as css_file:
            css_code = css_file.read()

        style_element = "<style>" + css_code + "</style>"
        self.bridge.style.emit(style_element)

    def draw_graph(self) -> None:
        self.view.load(self.url)

    @abstractmethod
    def random_graph(self) -> None:
        pass

    def update_plot_name(
        self,
        tab_label: str,
        method,
        demand_index: int | None = None,
        scenario_index: int | None = None,
    ) -> None:
        """Default export basename: ``{cs}_{tab}_{functional unit}_{method}_{scenario}``."""
        fu_label = None
        if demand_index is not None and 0 <= demand_index < len(getattr(self, "func_units", [])):
            import bw2data as bd

            from activity_browser.bwutils.commontasks import format_reference_flow_label

            key = list(self.func_units[demand_index].keys())[0]
            fu_label = format_reference_flow_label(bd.get_activity(key))
        scenario = None
        if getattr(self, "has_scenarios", False) and scenario_index is not None:
            scenarios = getattr(self, "scenarios", [])
            if 0 <= scenario_index < len(scenarios):
                scenario = scenarios[scenario_index]
        from activity_browser.bwutils.export_names import lca_export_basename

        self.plot_name = lca_export_basename(
            getattr(self, "cs", None), tab_label, fu_label, method, scenario
        )


ALL_FILTER = "All Files (*.*)"


def savefilepath(default_file_name: str, file_filter: str = ALL_FILTER):
    from activity_browser.bwutils import filesystem
    import bw2data as bd

    default = default_file_name or "Graph SVG Export"
    safe_name = bd.utils.safe_filename(default, add_hash=False)
    filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
        caption="Choose location to save svg",
        dir=os.path.join(filesystem.get_project_path(), safe_name),
        filter=file_filter,
    )
    return filepath


def to_svg(svg, default_file_name: str = "Figure"):
    """Export to .svg format."""
    filepath = savefilepath(default_file_name=default_file_name, file_filter="SVG (*.svg)")
    if filepath:
        if not filepath.endswith(".svg"):
            filepath += ".svg"
        svg_file = open(filepath, "w", encoding="utf-8")
        svg_file.write(svg)
        svg_file.close()


class Bridge(QObject):
    graph_ready = Signal(str)
    update_graph = Signal(object)
    style = Signal(str)

    def __init__(self, navigator: ABAbstractNavigator, parent=None):
        super().__init__(parent)
        self._navigator = navigator

    @Slot(str, name="node_clicked")
    def node_clicked(self, click_text: str):
        """Is called when a node is clicked in Javascript.
        Args:
            click_text: string of a serialized json dictionary describing
            - the node that was clicked on
            - mouse button and additional keys pressed
        """
        click_dict = json.loads(click_text)
        click_dict["key"] = (
            click_dict["database"],
            click_dict["id"],
        )  # since JSON does not know tuples
        logger.info(f"Click information: {click_dict}")  # TODO click_dict needs correcting
        self.update_graph.emit(click_dict)

    @Slot(str, name="download_triggered")
    def download_triggered(self, svg: str):
        """Is called when a node is clicked in Javascript.
        Args:
            svg: string of svg
        """
        to_svg(svg, default_file_name=self._navigator.plot_name)


class ABAbstractGraph(object):
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
        """Store the current graph in the"""
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
        """Writes the current model´s JSON representation to the specifies file."""
        if self.json_data:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, "w") as outfile:
                json.dump(self.json_data, outfile)

def get_static_js_path(file_name: str = "") -> str:
    return str(filesystem.get_package_path() / "static" / "javascript" / file_name)


def get_static_css_path(file_name: str = "") -> str:
    return str(filesystem.get_package_path() / "static" / "css" / file_name)