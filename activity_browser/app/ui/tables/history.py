# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction

from .table import ABTableWidget, ABTableItem
from ..icons import qicons
from ...signals import signals


class ActivitiesHistoryTable(ABTableWidget):
    MAX_LENGTH = 40
    COLUMNS = {
        0: "name",
        1: "reference product",
        2: "location",
        3: "unit",
    }
    HEADERS = ["Activity", "Reference Product", "Location", "Unit"]

    def __init__(self, *args):
        super(ActivitiesHistoryTable, self).__init__(*args)
        self.setDragEnabled(True)
        self.setRowCount(0)
        self.setColumnCount(len(self.HEADERS))
        self.setup_context_menu()
        self.connect_signals()

    def setup_context_menu(self):
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.open_left_tab_action = QAction(
            qicons.left, "Open in new tab", None
        )
        self.addAction(self.open_left_tab_action)
        self.open_left_tab_action.triggered.connect(
            lambda x: signals.open_activity_tab.emit(
                self.currentItem().key
            )
        )

    def connect_signals(self):
        self.itemDoubleClicked.connect(
            lambda x: signals.open_activity_tab.emit(self.currentItem().key)
        )
        self.itemDoubleClicked.connect(
            lambda x: signals.add_activity_to_history.emit(x.key)
        )
        signals.add_activity_to_history.connect(self.add_activity)
        signals.project_selected.connect(self.clear_history)

    def add_activity(self, key):
        for row in range(self.rowCount()):
            if self.item(row, 0).key == key:
                self.removeRow(row)
                break  # otherwise iterating over object that has changed

        ds = bw.get_activity(key)
        self.insertRow(0)
        for col, value in self.COLUMNS.items():
            if value == 'location':
                self.setItem(0, col, ABTableItem(str(ds.get(value, '')), key=key, color=value))
            else:
                self.setItem(0, col, ABTableItem(ds.get(value, ''), key=key, color=value))

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def clear_history(self):
        self.clear()
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setRowCount(0)
