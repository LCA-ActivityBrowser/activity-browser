# -*- coding: utf-8 -*-
from PySide2 import QtCore


class SankeySignals(QtCore.QObject):
    gt_ready = QtCore.Signal(dict)
    calculating_gt = QtCore.Signal()
    initial_sankey_ready = QtCore.Signal()


sankeysignals = SankeySignals()
