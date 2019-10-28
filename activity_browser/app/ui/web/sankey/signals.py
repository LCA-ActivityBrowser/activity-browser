# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal as Signal


class SankeySignals(QtCore.QObject):
    gt_ready = Signal(dict)
    calculating_gt = Signal()
    initial_sankey_ready = Signal()


sankeysignals = SankeySignals()
