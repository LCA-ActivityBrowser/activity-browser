# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from ..style import horizontal_line, header
from ..tables import ActivitiesHistoryTable


class HistoryTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(HistoryTab, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addWidget(header("Activity selection history:"))
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(ActivitiesHistoryTable(self))
        self.setLayout(self.layout)
