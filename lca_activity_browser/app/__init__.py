# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *


class Container(object):
    """Generic class that contains data attributes"""
    pass


from PyQt4 import QtGui
from .application import Application
import sys


def run_activity_browser():
    qapp = QtGui.QApplication(sys.argv)
    application = Application()
    application.show()
    sys.exit(qapp.exec_())
