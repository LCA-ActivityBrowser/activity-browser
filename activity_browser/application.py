# -*- coding: utf-8 -*-
import os

from PySide2.QtWidgets import QApplication
from PySide2.QtCore import QSysInfo, Qt, QCoreApplication, QObject

from activity_browser import log

class ABApplication(QApplication):
    _main_window = None
    _controllers = None

    @property
    def main_window(self) -> QObject:
        """Returns the main_window widget of the Activity Browser"""
        if self._main_window: return self._main_window
        raise Exception("main_window not yet initialized, did you try to access it during startup?")

    @main_window.setter
    def main_window(self, widget):
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
    supported = {'10.10', '10.11', '10.12', '10.13', '10.14', '10.15'}
    if QSysInfo.productVersion() not in supported:
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
        log.info("Info: GPU hardware acceleration disabled")

if QSysInfo.productType() in ["arch", "nixos"]:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
    log.info("Info: QtWebEngine sandbox disabled")

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

application = ABApplication()
