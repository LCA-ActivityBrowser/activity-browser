"""Custom page for debugging javascript code. Without this code,
    only console.error messages are printed to python output.
    This code will not tell you the javascript file that the error is in."""
from logging import getLogger

from qtpy.QtWebEngineWidgets import QWebEnginePage

log = getLogger(__name__)


class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: str, _: str):
        if level == QWebEnginePage.InfoMessageLevel:
            log.info(f"JS Info (Line {line}): {message}")
        elif level == QWebEnginePage.WarningMessageLevel:
            log.warning(f"JS Warning (Line {line}): {message}")
        elif level == QWebEnginePage.ErrorMessageLevel:
            log.error(f"JS Error (Line {line}): {message}")
        else:
            log.debug(f"JS Log (Line {line}): {message}")
