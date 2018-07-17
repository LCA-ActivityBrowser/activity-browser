# -*- coding: utf-8 -*-
from PyQt5 import QtCore


class GraphSignals(QtCore.QObject):
    gt_ready = QtCore.pyqtSignal(dict)
    calculating_gt = QtCore.pyqtSignal()
    graph_ready = QtCore.pyqtSignal()
    update_graph = QtCore.pyqtSignal(tuple)
    update_graph_expand = QtCore.pyqtSignal(tuple)
    update_graph_expand_upstream = QtCore.pyqtSignal(tuple)
    update_graph_reduce = QtCore.pyqtSignal(tuple)



graphsignals = GraphSignals()
