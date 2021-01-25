# -*- coding: utf-8 -*-
import os
import sys
import traceback

from PySide2.QtCore import __version__ as qt_version
from PySide2.QtWidgets import QApplication

from .application import Application
from .info import __version__

# https://bugreports.qt.io/browse/QTBUG-87014
os.environ['QT_MAC_WANTS_LAYER'] = '1'


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
