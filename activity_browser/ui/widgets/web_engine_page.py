from loguru import logger

from qtpy.QtWebEngineWidgets import QWebEnginePage


class ABWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: QWebEnginePage.JavaScriptConsoleMessageLevel, message: str, line: str, _: str):
        if level == QWebEnginePage.InfoMessageLevel:
            logger.info(f"JS Info (Line {line}): {message}")
        elif level == QWebEnginePage.WarningMessageLevel:
            logger.warning(f"JS Warning (Line {line}): {message}")
        elif level == QWebEnginePage.ErrorMessageLevel:
            logger.error(f"JS Error (Line {line}): {message}")
        else:
            logger.debug(f"JS Log (Line {line}): {message}")
