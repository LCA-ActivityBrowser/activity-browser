# -*- coding: utf-8 -*-
import os
from logging import getLogger

import qtpy
from qtpy.QtCore import QCoreApplication, QSysInfo, Qt
from qtpy.QtWidgets import QApplication, QStyleFactory, QMainWindow
from qtpy.QtGui import QFontDatabase

from activity_browser.static import fonts


log = getLogger(__name__)


class ABApplication(QApplication):
    _main_window = None
    _controllers = None

    windows = []

    @property
    def main_window(self) -> QMainWindow:
        """Returns the main_window widget of the Activity Browser"""
        if self._main_window:
            return self._main_window
        raise Exception(
            "main_window not yet initialized, did you try to access it during startup?"
        )

    @main_window.setter
    def main_window(self, widget: QMainWindow):
        self._main_window = widget

    def show(self):
        self.main_window.showMaximized()

    def close(self):
        for child in self.children():
            if hasattr(child, "close"):
                child.close()

    def deleteLater(self):
        self.main_window.deleteLater()


if QSysInfo.productType() == "osx":
    # https://bugreports.qt.io/browse/QTBUG-87014
    # https://bugreports.qt.io/browse/QTBUG-85546
    # https://github.com/mapeditor/tiled/issues/2845
    # https://doc.qt.io/qt-5/qoperatingsystemversion.html#MacOSBigSur-var
    supported = {"10.10", "10.11", "10.12", "10.13", "10.14", "10.15", "13.6"}
    if QSysInfo.productVersion() not in supported:
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
        log.info("Info: GPU hardware acceleration disabled")

# on macos buttons silently crashes the renderer without any logs
# confirmed that buttons works on the latest version of qt using pyside6
if QSysInfo.productType() in ["arch", "nixos", "osx"]:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "{} --no-sandbox".format(
        os.getenv("QTWEBENGINE_CHROMIUM_FLAGS")
    )
    log.info("Info: QtWebEngine sandbox disabled")

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

application = ABApplication()

QFontDatabase.addApplicationFont(fonts.__path__[0] + "/mono.ttf")
QFontDatabase.addApplicationFont(fonts.__path__[0] + "/ptsans.ttf")

if qtpy.PYSIDE6:
    application.setStyle(QStyleFactory().create("fusion"))

    font = application.font()
    font.setFamily("PT Sans")
    font.setPointSize(10)
    application.setFont(font)
    application.setAttribute(Qt.AA_DontShowIconsInMenus, True)
