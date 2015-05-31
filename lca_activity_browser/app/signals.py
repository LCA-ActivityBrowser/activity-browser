# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore


class Signals(QtCore.QObject):
    project_selected = QtCore.pyqtSignal(str)
    database_selected = QtCore.pyqtSignal(str)
    databases_changed = QtCore.pyqtSignal()
    method_selected = QtCore.pyqtSignal(tuple)
    activity_selected = QtCore.pyqtSignal(tuple)
    calculation_setup_selected = QtCore.pyqtSignal(str)

signals = Signals()
