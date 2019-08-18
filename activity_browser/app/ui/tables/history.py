# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QAbstractItemView, QAction, QMenu

from activity_browser.app.bwutils.commontasks import bw_keys_to_AB_names

from .table import ABTableWidget, ABTableItem
from .views import ABDataFrameView, dataframe_sync
from ..icons import qicons
from ...signals import signals


class ActivitiesHistoryTable(ABDataFrameView):
    COLUMNS = [
        "name",
        "reference product",
        "location",
        "unit",
    ]
    HEADERS = [bw_keys_to_AB_names[c] for c in COLUMNS] + ["key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._connect_signals()
        self.sync()

    def _connect_signals(self):
        self.doubleClicked.connect(self.open_tab_event)
        signals.add_activity_to_history.connect(self.add_activity)
        signals.project_selected.connect(self.sync)

    @dataframe_sync
    def sync(self, df=None):
        if df is None:
            df = pd.DataFrame([], columns=self.HEADERS)
        self.dataframe = df

    def contextMenuEvent(self, a0):
        menu = QMenu(self)
        menu.addAction(
            qicons.left, "Open in new tab", self.open_tab
        )
        menu.popup(QCursor.pos())
        menu.exec()

    @pyqtSlot()
    def open_tab(self):
        for proxy in self.selectedIndexes():
            self.open_tab_event(proxy)

    def open_tab_event(self, proxy):
        index = self.get_source_index(proxy)
        row = self.dataframe.iloc[index.row(), ]
        signals.open_activity_tab.emit(row["key"])
        self.add_activity(row["key"])

    @pyqtSlot(tuple)
    def add_activity(self, key: tuple) -> None:
        df = self.dataframe
        row = df.loc[df["key"].isin([key])]

        if not row.empty:
            # Perform reindexing with existing data
            df.drop(row.index, inplace=True)
            df = pd.concat([row, df]).reset_index(drop=True)
        else:
            # Build new row
            ds = bw.get_activity(key)
            data = {
                self.HEADERS[i]: ds.get(self.COLUMNS[i], "")
                for i in range(len(self.COLUMNS))
            }
            data["key"] = key
            row = pd.DataFrame(
                [data], index=[0], columns=self.HEADERS
            )
            df = pd.concat([row, df]).reset_index(drop=True)
        
        self.sync(df)

    def _resize(self):
        self.setColumnHidden(4, True)  # Hide the 'key' column
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


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
