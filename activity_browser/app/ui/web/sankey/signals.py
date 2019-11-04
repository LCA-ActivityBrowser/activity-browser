# -*- coding: utf-8 -*-
from PySide2 import QtCore
from PySide2.QtCore import Signal


class SankeySignals(QtCore.QObject):
    gt_ready = Signal(dict)
    calculating_gt = Signal()
    initial_sankey_ready = Signal()


sankeysignals = SankeySignals()
