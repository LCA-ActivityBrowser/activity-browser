# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets

from activity_browser.i18n import _

from ...ui.style import header, horizontal_line
from ...ui.tables import ActivitiesHistoryTable


class HistoryTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(HistoryTab, self).__init__(parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addWidget(header(_("Activity selection history:")))
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(ActivitiesHistoryTable(self))
        self.setLayout(self.layout)
