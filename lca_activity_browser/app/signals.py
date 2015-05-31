# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore


class Signals(QtCore.QObject):
    project_changed = QtCore.pyqtSignal(str)
    method_selected = QtCore.pyqtSignal(tuple)

signals = Signals()
