# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PySide2.QtCore import Slot
from PySide2.QtGui import QCursor
from PySide2.QtWidgets import QAbstractItemView, QMenu

from activity_browser.app.bwutils.commontasks import bw_keys_to_AB_names
from activity_browser.app.signals import signals

from .views import ABDataFrameView, dataframe_sync
from ..icons import qicons


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
        self.sync()
        self._connect_signals()

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
            qicons.right, "Open in new tab", self.open_tab
        )
        menu.popup(QCursor.pos())
        menu.exec()

    @Slot()
    def open_tab(self):
        """ Only a single row can be selected for the history,
        trigger the open_tab_event.
        """
        proxy = next(i for i in self.selectedIndexes())
        self.open_tab_event(proxy)

    def open_tab_event(self, proxy):
        index = self.get_source_index(proxy)
        key = self.dataframe.iloc[index.row(), ]["key"]
        signals.open_activity_tab.emit(key)
        self.add_activity(key)

    @Slot(tuple)
    def add_activity(self, key: tuple) -> None:
        row = self.dataframe.loc[self.dataframe["key"].isin([key])]

        if not row.empty:
            # As data now exists in row, drop it from the dataframe
            self.dataframe.drop(row.index, inplace=True)
        else:
            # Data didn't exist, so build a new row with the key
            ds = bw.get_activity(key)
            data = {
                self.HEADERS[i]: ds.get(self.COLUMNS[i], "")
                for i in range(len(self.COLUMNS))
            }
            data["key"] = key
            row = pd.DataFrame(
                [data], index=[0], columns=self.HEADERS
            )

        # Rebuild model with dataframe, added activity is placed at start
        self.sync(pd.concat([row, self.dataframe]).reset_index(drop=True))

    def _resize(self):
        self.setColumnHidden(4, True)  # Hide the 'key' column
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
