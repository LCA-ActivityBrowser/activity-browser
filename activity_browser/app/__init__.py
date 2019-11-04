# -*- coding: utf-8 -*-
import sys
import traceback

from PySide2 import QtWidgets, QtCore

from .application import Application
from .ui.style import default_font


def run_activity_browser():
    qapp = QtWidgets.QApplication(sys.argv)
    # qapp.setFont(default_font)
    application = Application()
    application.show()
    print("Qt Version:", QtCore.__version__)

    def exception_hook(*args):
        print(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(qapp.exec_())
