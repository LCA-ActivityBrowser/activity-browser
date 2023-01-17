# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PySide2.QtCore import Slot, QModelIndex

from activity_browser.bwutils import commontasks as bc
from activity_browser.signals import signals
from .base import PandasModel


class ActivitiesHistoryModel(PandasModel):
    HEADERS = ["Activity", "Product", "Location", "Unit", "key"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.key_col = 0
        signals.project_selected.connect(self.sync)
        signals.add_activity_to_history.connect(self.add_activity)

    def sync(self, df=None):
        if df is None:
            df = pd.DataFrame([], columns=self.HEADERS)
        self._dataframe = df
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

    @Slot(tuple, name="addActivityToHistory")
    def add_activity(self, key: tuple) -> None:
        row = self._dataframe.loc[self._dataframe["key"].isin([key])]

        if not row.empty:
            # As data now exists in row, drop it from the dataframe
            self._dataframe.drop(row.index, inplace=True)
        else:
            # Data didn't exist, so build a new row with the key
            ds = bw.get_activity(key)
            data = {
                h: ds.get(bc.AB_names_to_bw_keys.get(h), "")
                for h in self.HEADERS[:-1]
            }
            data["key"] = key
            row = pd.DataFrame(
                [data], index=[0], columns=self.HEADERS
            )

        # Rebuild model with dataframe, added activity is placed at start
        self.sync(pd.concat([row, self._dataframe]).reset_index(drop=True))

    @Slot(QModelIndex, name="openHistoryTab")
    def open_tab_event(self, proxy: QModelIndex) -> None:
        idx = self.proxy_to_source(proxy)
        key = self._dataframe.iat[idx.row(), self.key_col]
        signals.safe_open_activity_tab.emit(key)
        self.add_activity(key)
