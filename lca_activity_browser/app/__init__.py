# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *


class Container(object):
    """Generic class that contains data attributes"""
    pass


from PyQt5 import QtWidgets
from .application import Application
import sys
import traceback


def run_activity_browser():
    qapp = QtWidgets.QApplication(sys.argv)
    application = Application()
    application.show()

    def exception_hook(*args):
        print(''.join(traceback.format_exception(*args)))

    sys.excepthook = exception_hook

    sys.exit(qapp.exec_())
