import html
import json
import os
from abc import abstractmethod
from copy import deepcopy
from typing import Type
from logging import getLogger

from PySide2 import QtWebChannel, QtWebEngineWidgets, QtWidgets
from PySide2.QtCore import QObject, Qt, QUrl, Signal, Slot

from activity_browser import ab_settings, signals
from activity_browser.i18n import _, current_language
from activity_browser.mod import bw2data as bd

from ... import utils
from ...ui.icons import qicons
from . import webutils

log = getLogger(__name__)


class BaseNavigatorWidget(QtWidgets.QWidget):
    HELP_TEXT = ("This help text describes how to use the graph.",)
    HTML_FILE = ""
    PAGE_TITLE = "Graph"

    def __init__(self, parent=None, css_file: str = "", *args, **kwargs):
        super().__init__(parent)

        # Graph object subclassed from BaseGraph.
        self.graph: Type[BaseGraph]

        # Setup JS / Qt interactions
        self.bridge = Bridge(self)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.view = QtWebEngineWidgets.QWebEngineView(self)
        self.view.loadFinished.connect(self.load_finished_handler)
        self.view.setContextMenuPolicy(Qt.PreventContextMenu)
        self.view.page().setWebChannel(self.channel)
        self.url = QUrl.fromLocalFile(self.HTML_FILE)
        self.html_base_url = QUrl.fromLocalFile(
            os.path.dirname(self.HTML_FILE) + os.path.sep
        )
        self.css_file = css_file

        # Various Qt objects
        help_text = (
            _(self.HELP_TEXT)
            if isinstance(self.HELP_TEXT, str)
            else "\n".join(_(line) for line in self.HELP_TEXT)
        )
        self.label_help = QtWidgets.QLabel(help_text)
        self.button_toggle_help = QtWidgets.QPushButton(_("Help"))
        self.button_back = QtWidgets.QPushButton(qicons.backward, "")
        self.button_back.setToolTip(_("Back"))
        self.button_forward = QtWidgets.QPushButton(qicons.forward, "")
        self.button_forward.setToolTip(_("Forward"))
        self.button_refresh = QtWidgets.QPushButton(_("Refresh HTML"))
        self.button_random_activity = QtWidgets.QPushButton(_("Random Activity"))

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
            signals.new_statusbar_message.emit(_("Going forward."))
            self.send_json()
        else:
            signals.new_statusbar_message.emit(_("No data to go forward to."))

    def go_back(self) -> None:
        if self.graph.back():
            signals.new_statusbar_message.emit(_("Going back."))
            self.send_json()
        else:
            signals.new_statusbar_message.emit(_("No data to go back to."))

    def send_json(self) -> None:
        self.bridge.graph_ready.emit(self.graph.json_data)
        css_path = webutils.get_static_css_path(self.css_file)
        css_code = utils.read_file_text(css_path)
        style_element = "<style>" + css_code + "</style>"
        self.bridge.style.emit(style_element)

    def draw_graph(self) -> None:
        self.view.setHtml(self.render_html(), self.html_base_url)

    def render_html(self) -> str:
        """Render the graph page with fixed UI text in the active language."""

        source = utils.read_file_text(self.HTML_FILE)
        translations = {
            "individual_impact": _("Individual impact"),
            "cumulative_impact": _("Cumulative impact"),
        }
        replacements = {
            "LANGUAGE": current_language().replace("_", "-"),
            "PAGE_TITLE": _(self.PAGE_TITLE),
            "RESET_ZOOM": _("Reset Zoom"),
            "DOWNLOAD_SVG": _("Download SVG"),
        }
        for name, value in replacements.items():
            source = source.replace(f"{{{{{name}}}}}", html.escape(value))

        translations_json = json.dumps(translations, ensure_ascii=False).replace(
            "</", "<\\/"
        )
        return source.replace("{{TRANSLATIONS_JSON}}", translations_json)

    @abstractmethod
    def random_graph(self) -> None:
        pass


ALL_FILTER = "All Files (*.*)"


def savefilepath(default_file_name: str, file_filter: str = None):
    default = default_file_name or _("Graph SVG Export")
    safe_name = bd.utils.safe_filename(default, add_hash=False)
    filepath = QtWidgets.QFileDialog.getSaveFileName(
        caption=_("Choose location to save SVG"),
        dir=os.path.join(ab_settings.data_dir, safe_name),
        filter=file_filter or _("All Files (*.*)"),
    )[0]
    return filepath


def to_svg(svg):
    """Export to .svg format."""
    # TODO: Exported filename
    filepath = savefilepath(default_file_name="svg_export", file_filter="SVG (*.svg)")
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
        log.info(f"Click information: {click_dict}")  # TODO click_dict needs correcting
        self.update_graph.emit(click_dict)

    @Slot(str, name="download_triggered")
    def download_triggered(self, svg: str):
        """Is called when a node is clicked in Javascript.
        Args:
            svg: string of svg
        """
        to_svg(svg)


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
