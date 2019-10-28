# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal as Signal


class GraphSignals(QtCore.QObject):
    update_graph = Signal(dict)

graphsignals = GraphSignals()
