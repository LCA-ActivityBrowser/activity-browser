# -*- coding: utf-8 -*-
import sys
import traceback

from PySide2 import QtWidgets

from .application import Application


def run_activity_browser():
    qapp = QtWidgets.QApplication(sys.argv)
    application = Application()
    application.show()

    def exception_hook(*args):
        print(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(qapp.exec_())
