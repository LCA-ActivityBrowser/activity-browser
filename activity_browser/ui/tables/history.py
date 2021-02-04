# -*- coding: utf-8 -*-
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QAbstractItemView, QMenu

from ...signals import signals
from ..icons import qicons
from .models import ActivitiesHistoryModel
from .views import ABDataFrameView


class ActivitiesHistoryTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model = ActivitiesHistoryModel(self)
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(self.model.open_tab_event)
        signals.project_selected.connect(self.sync)

    def sync(self, df=None):
        self.model.sync(df)
        self._resize()

    def contextMenuEvent(self, a0):
        menu = QMenu(self)
        menu.addAction(
            qicons.right, "Open in new tab", self.open_tab
        )
        menu.exec_(a0.globalPos())

    @Slot(name="openTab")
    def open_tab(self):
        """ Only a single row can be selected for the history,
        trigger the open_tab_event.
        """
        self.model.open_tab_event(self.currentIndex())

    def _resize(self):
        self.setColumnHidden(self.model.key_col, True)  # Hide the 'key' column
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
