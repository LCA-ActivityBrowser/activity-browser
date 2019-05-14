# -*- coding: utf-8 -*-
from PyQt5 import QtCore


class GraphSignals(QtCore.QObject):
    update_graph = QtCore.pyqtSignal(dict)

graphsignals = GraphSignals()
