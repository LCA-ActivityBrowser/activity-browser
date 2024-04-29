# -*- coding: utf-8 -*-
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QAbstractItemView, QMenu

from ..icons import qicons
from .models import ActivitiesHistoryModel
from .views import ABDataFrameView


class ActivitiesHistoryTable(ABDataFrameView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.model = ActivitiesHistoryModel(self)
        self.doubleClicked.connect(self.model.open_tab_event)
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QMenu(self)
        menu.addAction(
            qicons.right, "Open in new tab", self.open_tab
        )
        menu.exec_(event.globalPos())

    @Slot(name="openTab")
    def open_tab(self):
        """ Only a single row can be selected for the history,
        trigger the open_tab_event.
        """
        self.model.open_tab_event(self.currentIndex())

    @Slot(name="resizeView")
    def custom_view_sizing(self):
        self.setColumnHidden(self.model.key_col, True)  # Hide the 'key' column
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
