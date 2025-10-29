"""Custom page for debugging javascript code. Without this code,
    only console.error messages are printed to python output.
    This code will not tell you the javascript file that the error is in."""
from loguru import logger

from qtpy.QtWebEngineWidgets import QWebEnginePage




class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: str, _: str):
        if level == QWebEnginePage.InfoMessageLevel:
            logger.info(f"JS Info (Line {line}): {message}")
        elif level == QWebEnginePage.WarningMessageLevel:
            logger.warning(f"JS Warning (Line {line}): {message}")
        elif level == QWebEnginePage.ErrorMessageLevel:
            logger.error(f"JS Error (Line {line}): {message}")
        else:
            logger.debug(f"JS Log (Line {line}): {message}")
