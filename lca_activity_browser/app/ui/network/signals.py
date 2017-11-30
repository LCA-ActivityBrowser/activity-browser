# -*- coding: utf-8 -*-
from PyQt5 import QtCore


class SankeySignals(QtCore.QObject):
    gt_ready = QtCore.pyqtSignal(dict)
    calculating_gt = QtCore.pyqtSignal()
    initial_sankey_ready = QtCore.pyqtSignal()


sankeysignals = SankeySignals()
