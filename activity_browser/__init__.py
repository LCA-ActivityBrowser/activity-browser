# -*- coding: utf-8 -*-
import os
import sys
import traceback

from PySide2.QtCore import QSysInfo, __version__ as qt_version
from PySide2.QtWidgets import QApplication

from .application import Application
from .plugin import Plugin
from .info import __version__


# https://bugreports.qt.io/browse/QTBUG-87014
# https://bugreports.qt.io/browse/QTBUG-85546
# https://github.com/mapeditor/tiled/issues/2845
# https://doc.qt.io/qt-5/qoperatingsystemversion.html#MacOSBigSur-var
if QSysInfo.productType() == "osx":
    supported = {'10.10', '10.11', '10.12', '10.13', '10.14', '10.15'}
    if QSysInfo.productVersion() not in supported:
        os.environ["QT_MAC_WANTS_LAYER"] = "1"
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
        print("Info: GPU hardware acceleration disabled")


def run_activity_browser():
    qapp = QApplication(sys.argv)
    # qapp.setFont(default_font)
    application = Application()
    application.show()
    print("Qt Version:", qt_version)

    def exception_hook(*args):
        print(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(qapp.exec_())
