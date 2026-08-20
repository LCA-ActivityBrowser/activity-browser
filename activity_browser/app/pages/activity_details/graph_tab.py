import json
import os
import time
from loguru import logger

from qtpy import QtWebChannel, QtWebEngineWidgets, QtWidgets
from qtpy.QtCore import QObject, Qt, QUrl, Signal, SignalInstance, Slot

import bw2data as bd

from activity_browser import static, app
from activity_browser.app.pages.lca_results.style import show_open_process_menu
from activity_browser.bwutils.commontasks import (
    database_is_locked,
    get_exchange_type,
    refresh_node,
)
from activity_browser.bwutils.graph_explorer.inventory import BrightwayInventory
from activity_browser.bwutils.graph_explorer.explorer import FlowKey, GraphExplorer
from activity_browser.ui import widgets
from activity_browser.ui.icons import qicons

GRAPH_HELP = """
Graph explorer

Scroll to zoom; drag the background to pan.

The first view is the opened process plus counterparts listed on its
inputs and outputs (at most 10 per side). Functional flows of the opened
process are drawn in red (thicker) to a dashed box ("N consumers" or
"N suppliers"). Click that flow, box, or the matching triangle to show
those processes (10 at a time). Listed leftovers are a dashed
"N more processes" box.

"Show only direct up-/downstream flows" (on by default) draws only
the flows you expanded along. Uncheck it to also draw every other
technosphere flow among the processes already on the canvas.

Click a triangle to expand consumers of the opened process (same as
clicking its functional flow). For other processes, the triangle expands
a side that has no processes shown yet.
If listed inputs/outputs remain, a dashed box ("N more processes") pages
the rest (10 at a time). Collapse is the inward triangle.

Left-click a process box to select it.
Right-click a box for Open process.
Alt+click or Delete: remove a process from the graph.

Product flows are solid; waste flows (and production inputs) are dashed.
Substitution flows are green (substituting process toward the avoided process).
A filled black circle marks the functional end of a flow.
Amounts on labels are physical quantities (always positive).

Reset returns to the opened process and its direct upstream and downstream.
Fit fits the current graph in the window.
""".strip()


def _metadata_cell(row, name: str) -> str:
    if name not in getattr(row, "index", []):
        return ""
    val = row[name]
    if val is None:
        return ""
    try:
        if val != val:
            return ""
    except (TypeError, ValueError):
        pass
    return str(val)


def process_card_from_metadata(process_id: int) -> dict | None:
    """Display fields from MetaDataStore; BrightwayInventory falls back if this is None."""
    df = app.metadata.dataframe
    if df is None or df.empty or "id" not in df.columns:
        return None
    hit = df.loc[df["id"] == int(process_id)]
    if hit.empty:
        return None
    row = hit.iloc[0]
    database = _metadata_cell(row, "database")
    key = hit.index[0]
    if not database and isinstance(key, tuple) and key:
        database = str(key[0])
    node_type = _metadata_cell(row, "type")
    return {
        "name": _metadata_cell(row, "name"),
        "location": _metadata_cell(row, "location"),
        "database": database,
        "product": _metadata_cell(row, "product") or _metadata_cell(row, "reference product"),
        "type": node_type or None,
    }


class GraphTab(QtWidgets.QWidget):
    """Activity Details Graph explorer (built on first Graph-tab show)."""

    def __init__(self, activity, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.activity = refresh_node(activity)
        self._shown = False
        self._js_ready = False
        self.explorer: GraphExplorer | None = None

        self.bridge = Bridge(self)
        self.backend = GraphBackend(self)
        self.url = QUrl.fromLocalFile(os.path.join(static.__path__[0], "graph_explorer.html"))

        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.channel.registerObject("backend", self.backend)

        self.page = Page()
        self.page.setWebChannel(self.channel)

        self.view = GraphView(self)
        self.view.setPage(self.page)

        self.reset_btn = QtWidgets.QPushButton("Reset")
        self.reset_btn.setToolTip("Reset graph and view")
        self.reset_btn.clicked.connect(self.backend.reset_graph)

        self.fit_btn = QtWidgets.QPushButton("Fit")
        self.fit_btn.setToolTip("Fit the current graph in the window")
        self.fit_btn.clicked.connect(self._fit_view)

        self.help_btn = QtWidgets.QToolButton(self)
        self.help_btn.setIcon(qicons.question)
        self.help_btn.setAutoRaise(True)
        self.help_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.help_btn.setToolTip("Left click for help on the Graph explorer")
        self.help_btn.clicked.connect(self._show_help)

        self.direct_only_cb = QtWidgets.QCheckBox("Show only direct up-/downstream flows")
        self.direct_only_cb.setChecked(True)
        self.direct_only_cb.setToolTip(
            "When adding processes, show only the expanded up-/downstream flows "
            "(cleaner). Uncheck to also show every technosphere flow among the "
            "processes already in the graph."
        )
        self.direct_only_cb.stateChanged.connect(self._on_direct_only)

        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(8, 6, 8, 6)
        bar.setSpacing(8)
        bar.addWidget(self.reset_btn)
        bar.addWidget(self.fit_btn)
        bar.addSpacing(16)
        bar.addWidget(self.direct_only_cb)
        bar.addStretch(1)
        bar.addWidget(self.help_btn)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(bar)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.bridge.ready.connect(self._on_js_ready)

    @property
    def has_been_shown(self) -> bool:
        return self._shown

    def ensure_loaded(self):
        self._shown = True
        if not self.view.url().isValid() or self.view.url().isEmpty():
            self.view.setUrl(self.url)
        if self._js_ready:
            self.sync()

    def _on_js_ready(self):
        self._js_ready = True
        if self._shown:
            self.sync()

    def sync(self):
        if not self._shown:
            return
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")
        self.activity = refresh_node(self.activity)
        if self.explorer is None or self.explorer.center_id != self.activity.id:
            t0 = time.perf_counter()
            self.explorer = GraphExplorer(
                self.activity.id, BrightwayInventory(process_card_from_metadata)
            )
            self.explorer.direct_only = self.direct_only_cb.isChecked()
            logger.debug(
                f"Graph explorer first paint {(time.perf_counter() - t0) * 1000:.0f} ms"
            )
        else:
            self.explorer.refresh_listed_exchanges()
        self._emit()

    def _emit(self):
        if self.explorer is None or not self._js_ready:
            return
        t0 = time.perf_counter()
        payload = self.explorer.payload()
        t1 = time.perf_counter()
        blob = json.dumps(payload)
        t2 = time.perf_counter()
        n_proc = sum(1 for n in payload["nodes"] if n.get("kind") == "process")
        logger.debug(
            f"Graph explorer payload {(t1 - t0) * 1000:.0f} ms, "
            f"json {(t2 - t1) * 1000:.0f} ms, {n_proc} processes, "
            f"{len(payload['edges'])} edges"
        )
        self.bridge.update_graph.emit(blob)

    def _on_direct_only(self):
        if self.explorer is None:
            return
        self.explorer.direct_only = self.direct_only_cb.isChecked()
        self._emit()

    def _fit_view(self):
        self.view.page().runJavaScript(
            "if (typeof abFitGraphExplorer === 'function') { abFitGraphExplorer(); }"
        )

    def _show_help(self):
        QtWidgets.QMessageBox.question(
            self,
            "Graph explorer",
            GRAPH_HELP,
            QtWidgets.QMessageBox.Ok,
            QtWidgets.QMessageBox.Ok,
        )


class GraphView(QtWebEngineWidgets.QWebEngineView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.overlay = None

    def dragEnterEvent(self, event):
        if database_is_locked(self.parent().activity["database"]):
            return
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            self.overlay = widgets.ABDropOverlay(self)
            self.overlay.show()
            event.accept()

    def dragLeaveEvent(self, event):
        if self.overlay is not None:
            self.overlay.deleteLater()
            self.overlay = None

    def dropEvent(self, event):
        logger.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        if self.overlay is not None:
            self.overlay.deleteLater()
            self.overlay = None
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        exchanges = {"technosphere": set(), "biosphere": set()}
        for key in keys:
            if exc_type := get_exchange_type(key):
                exchanges[exc_type].add(key)
        for exc_type, node_keys in exchanges.items():
            app.actions.ExchangeNew.run(node_keys, self.parent().activity.key, exc_type)


class GraphBackend(QObject):
    def __init__(self, graph_tab: GraphTab, parent=None):
        super().__init__(parent)
        self.graph_tab = graph_tab

    def _explorer(self) -> GraphExplorer | None:
        return self.graph_tab.explorer

    @Slot(str, str)
    def expand_flow(self, host_id: str, flow_json: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.expand_flow(int(host_id), FlowKey.from_dict(json.loads(flow_json)))
        self.graph_tab._emit()

    @Slot(str, str)
    def expand_listed_side(self, process_id: str, side: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.expand_listed_side(int(process_id), side)
        self.graph_tab._emit()

    @Slot(str, str)
    def expand_side(self, process_id: str, side: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.expand_side(int(process_id), side)
        self.graph_tab._emit()

    @Slot(str, str)
    def collapse_side(self, process_id: str, side: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.collapse_side(int(process_id), side)
        self.graph_tab._emit()

    @Slot(str)
    def remove_process(self, process_id: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.remove_process(int(process_id))
        self.graph_tab._emit()

    @Slot(str)
    def select_process(self, process_id: str):
        explorer = self._explorer()
        if explorer is None:
            return
        explorer.select(int(process_id))
        self.graph_tab._emit()

    @Slot()
    def reset_graph(self):
        tab = self.graph_tab
        if tab.explorer is None:
            return
        center = tab.explorer.center_id
        inv = tab.explorer.inventory
        invalidate = getattr(inv, "invalidate", None)
        if callable(invalidate):
            invalidate()
        tab.explorer = GraphExplorer(center, inv)
        tab.explorer.direct_only = tab.direct_only_cb.isChecked()
        tab._emit()

    @Slot(str)
    def open_process(self, process_id: str):
        explorer = self._explorer()
        if explorer is None:
            return
        try:
            node = bd.get_node(id=int(process_id))
        except Exception:
            node = None
        show_open_process_menu(self.graph_tab, [node] if node is not None else [])


class Bridge(QObject):
    update_graph: SignalInstance = Signal(str)
    ready: SignalInstance = Signal()

    @Slot()
    def is_ready(self):
        self.ready.emit()


class Page(QtWebEngineWidgets.QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message: str, line: str, _: str):
        if level == QtWebEngineWidgets.QWebEnginePage.InfoMessageLevel:
            logger.info(f"JS Info (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.WarningMessageLevel:
            logger.warning(f"JS Warning (Line {line}): {message}")
        elif level == QtWebEngineWidgets.QWebEnginePage.ErrorMessageLevel:
            logger.error(f"JS Error (Line {line}): {message}")
        else:
            logger.debug(f"JS Log (Line {line}): {message}")
