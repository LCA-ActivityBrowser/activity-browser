# -*- coding: utf-8 -*-
from PySide2 import QtCore
from PySide2.QtCore import Signal


class GraphSignals(QtCore.QObject):
    update_graph = Signal(dict)

graphsignals = GraphSignals()
