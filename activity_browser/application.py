# -*- coding: utf-8 -*-
import sys
import os

from PySide2.QtWidgets import QApplication
from PySide2.QtCore import QSysInfo

from activity_browser import log
from .controllers import controllers


class ABApplication(QApplication):
    _main_window = None

    def __init__(self):
        super().__init__(sys.argv)

    @property
    def main_window(self):
        """Returns the main_window widget of the Activity Browser"""
        if self._main_window: return self._main_window
        raise Exception("main_window not yet initialized, did you try to access it during startup?")

    @main_window.setter
    def main_window(self, widget):
        self._main_window = widget
        for attr, controller in controllers.items():
            setattr(self, attr, controller(self.main_window))

    def show(self):
        self.main_window.showMaximized()

    def close(self):
        self.plugin_controller.close_plugins()
        self.main_window.close()

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

if QSysInfo.productType() in ["arch","nixos"]:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
    log.info("Info: QtWebEngine sandbox disabled")

application = ABApplication()