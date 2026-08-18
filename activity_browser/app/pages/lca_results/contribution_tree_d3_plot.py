"""D3 WebEngine host for the Contribution Tree plot.

Thin Qt wrapper: Python pushes ``d3_plot_payload`` JSON; JavaScript emits click ids.
"""

from __future__ import annotations

import json
from typing import Callable

from loguru import logger
from qtpy import QtCore, QtGui, QtWebChannel, QtWebEngineWidgets, QtWidgets
from qtpy.QtCore import QObject, QUrl, Signal, Slot

from activity_browser import app
from activity_browser.bwutils.contribution_tree import d3_plot_payload
from activity_browser.bwutils.filesystem import get_package_path
from activity_browser.ui.widgets.web_engine_page import ABWebEnginePage

from .style import app_is_dark, inject_qt_ui_font

HTML_FILE = str(get_package_path() / "static" / "contribution_tree_plot.html")


def partition_segment_edge_color(*, dark: bool) -> str:
    """Contrast stroke for D3 partition segments (matches ``graph_theme.css``)."""
    return "#c5c5c5" if dark else "#333333"


class ContributionTreeD3Bridge(QObject):
    """WebChannel object: Python → JSON plot, JavaScript → click_uid."""

    update_plot = Signal(str)
    ready = Signal()
    segment_clicked = Signal(int)
    context_requested = Signal(object)

    @Slot()
    def is_ready(self) -> None:
        self.ready.emit()

    @Slot(int)
    def click_segment(self, uid: int) -> None:
        self.segment_clicked.emit(int(uid))

    @Slot(str)
    def context_segment(self, payload: str) -> None:
        self.context_requested.emit(json.loads(payload))


class ContributionTreeD3Plot(QtWidgets.QWidget):
    """WebEngine pane that draws the Contribution Tree plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self._js_ready = False
        self._pending_json: str | None = None
        self._on_segment_clicked: Callable[[dict], None] | None = None
        self._on_segment_context: Callable[[dict], None] | None = None

        self.bridge = ContributionTreeD3Bridge(self)
        self.channel = QtWebChannel.QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)

        self.view = QtWebEngineWidgets.QWebEngineView(self)
        self.page = ABWebEnginePage(self.view)
        self.view.setPage(self.page)
        self.view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.PreventContextMenu)
        self.view.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.page.setWebChannel(self.channel)
        self.view.setUrl(QUrl.fromLocalFile(HTML_FILE))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.bridge.ready.connect(self._on_js_ready)
        self.bridge.segment_clicked.connect(self._on_js_click)
        self.bridge.context_requested.connect(self._on_js_context)
        self.view.loadFinished.connect(self._apply_web_theme)
        app.application.theme_changed.connect(self._apply_web_theme)

    def set_segment_click_handler(
        self, handler: Callable[[dict], None] | None
    ) -> None:
        self._on_segment_clicked = handler

    def set_segment_context_handler(
        self, handler: Callable[[dict], None] | None
    ) -> None:
        self._on_segment_context = handler

    def style_from_palette(self) -> dict:
        pal = app.application.palette()
        bg = pal.color(QtGui.QPalette.ColorRole.Window)
        fg = pal.color(QtGui.QPalette.ColorRole.WindowText)
        dark = app_is_dark()
        return {
            "background": bg.name(),
            "text": fg.name(),
            "muted": fg.name(),
            "edge": partition_segment_edge_color(dark=dark),
            "dark": dark,
        }

    def set_payload(self, payload: dict) -> None:
        self._pending_json = json.dumps(payload)
        self._flush_payload()

    def show_empty(self, message: str | None = None) -> None:
        self.set_payload(
            d3_plot_payload(
                [],
                "icicle",
                empty_message=message or "",
                style=self.style_from_palette(),
            )
        )

    def export_figure(self, path: str, selected_filter: str = "") -> None:
        want_png = "png" in (selected_filter or "").lower() or path.lower().endswith(
            ".png"
        )
        self.page.runJavaScript(
            "typeof buildContributionTreeSvgExport === 'function' "
            "? buildContributionTreeSvgExport() : null",
            lambda svg, p=path, png=want_png: self._finish_export(svg, p, png),
        )

    def notify_viewport(self, *, reset_zoom: bool = False, force: bool = False) -> None:
        w = max(0, int(self.width()))
        h = max(0, int(self.height()))
        rz = "true" if reset_zoom else "false"
        fr = "true" if force else "false"
        self.page.runJavaScript(
            "if (window.abTreeViewportChanged) window.abTreeViewportChanged("
            f"{{resetZoom: {rz}, force: {fr}, width: {w}, height: {h}}});"
        )

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        old = event.oldSize()
        new = event.size()
        if (
            old.isValid()
            and abs(new.width() - old.width()) < 2
            and abs(new.height() - old.height()) < 2
        ):
            return
        self.notify_viewport(force=True)

    @Slot()
    def _apply_web_theme(self, *_args) -> None:
        QtCore.QTimer.singleShot(0, self._lock_web_theme)

    def _lock_web_theme(self) -> None:
        dark = "true" if app_is_dark() else "false"
        self.page.runJavaScript(
            "if (window.abLockGraphTheme) window.abLockGraphTheme(" + dark + ");"
        )
        inject_qt_ui_font(self.page)

    def _finish_export(self, svg, path: str, want_png: bool) -> None:
        try:
            if want_png:
                image = _rasterize_svg(svg) if svg else None
                if image is None or image.isNull():
                    pix = self.view.grab()
                    image = pix.toImage() if pix and not pix.isNull() else None
                if image is None or image.isNull():
                    raise RuntimeError("Could not capture the plot.")
                if not path.lower().endswith(".png"):
                    path += ".png"
                image.save(path, "PNG")
            else:
                if not svg:
                    raise RuntimeError("Could not capture the plot SVG.")
                if not path.lower().endswith(".svg"):
                    path += ".svg"
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(svg)
            logger.info(f"Contribution tree plot exported to {path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Export failed", str(exc))

    @Slot()
    def _on_js_ready(self) -> None:
        self._js_ready = True
        self._flush_payload()

    def _flush_payload(self) -> None:
        if self._js_ready and self._pending_json is not None:
            self.bridge.update_plot.emit(self._pending_json)

    @Slot(int)
    def _on_js_click(self, uid: int) -> None:
        if self._on_segment_clicked is None:
            return
        target = int(uid)
        self._on_segment_clicked({"unique_id": target, "toggle_uid": target})

    @Slot(object)
    def _on_js_context(self, payload: dict) -> None:
        if self._on_segment_context is None or not isinstance(payload, dict):
            return
        self._on_segment_context(payload)


def _rasterize_svg(svg: str) -> QtGui.QImage | None:
    """Turn SVG markup into a PNG-ready QImage. None if QtSvg is unavailable."""
    if not svg:
        return None
    try:
        from qtpy.QtSvg import QSvgRenderer
    except ImportError:
        return None
    renderer = QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        return None
    size = renderer.defaultSize()
    if size.width() < 1 or size.height() < 1:
        size = QtCore.QSize(1200, 800)
    image = QtGui.QImage(
        size.width() * 2, size.height() * 2, QtGui.QImage.Format.Format_ARGB32
    )
    fill = QtGui.QColor("#2b2b2b" if app_is_dark() else "white")
    image.fill(fill)
    painter = QtGui.QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return image
