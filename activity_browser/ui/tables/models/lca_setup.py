# -*- coding: utf-8 -*-
from typing import Iterable

import brightway2 as bw
from bw2data.backends.peewee import ActivityDataset
import pandas as pd
from PySide2.QtCore import QModelIndex, Slot

from activity_browser.bwutils import commontasks as bc
from activity_browser.signals import signals
from .base import EditablePandasModel, PandasModel


class CSActivityModel(EditablePandasModel):
    HEADERS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database"
    ]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.current_cs = None
        self.key_col = 0
        signals.calculation_setup_selected.connect(self.sync)
        signals.databases_changed.connect(self.sync)
        # after editing the model, signal that the calculation setup has changed.
        self.dataChanged.connect(lambda: signals.calculation_setup_changed.emit())

    @property
    def activities(self) -> list:
        selection = self._dataframe.loc[:, ["Amount", "key"]].to_dict(orient="records")
        return [{x["key"]: x["Amount"]} for x in selection]

    def get_key(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.key_col]

    @Slot(str, name="syncModel")
    def sync(self, name: str = None):
        if self.current_cs is None and name is None:
            raise ValueError("'name' cannot be None if no name is set")
        if name:
            assert name in bw.calculation_setups, "Given calculation setup does not exist."
            self.current_cs = name

        fus = bw.calculation_setups[self.current_cs].get('inv', [])
        df = pd.DataFrame([
            self.build_row(key, amount) for func_unit in fus
            for key, amount in func_unit.items()
        ], columns=self.HEADERS + ["key"])
        # Drop rows where the fu key was invalid in some way.
        self._dataframe = df.dropna().reset_index(drop=True)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

    def build_row(self, key: tuple, amount: float = 1.0) -> dict:
        try:
            act = bw.get_activity(key)
            if act.get("type", "process") != "process":
                raise TypeError("Activity is not of type 'process'")
            row = {
                key: act.get(bc.AB_names_to_bw_keys[key], "")
                for key in self.HEADERS
            }
            row.update({"Amount": amount, "key": key})
            return row
        except (TypeError, ActivityDataset.DoesNotExist):
            print("Could not load key in Calculation Setup: ", key)
            return {}

    @Slot(name="deleteRows")
    def delete_rows(self, proxies: list) -> None:
        indices = (self.proxy_to_source(p) for p in proxies)
        rows = [i.row() for i in indices]
        self._dataframe = self._dataframe.drop(rows, axis=0).reset_index(drop=True)
        self.updated.emit()
        signals.calculation_setup_changed.emit()  # Trigger update of CS in brightway

    def include_activities(self, new_activities: Iterable) -> None:
        existing = set(self._dataframe.loc[:, "key"])
        data = []
        for fu in (f for f in new_activities if existing.isdisjoint(f)):
            k, v = zip(*fu.items())
            data.append(self.build_row(k[0], v[0]))
        if data:
            self._dataframe = self._dataframe.append(data, ignore_index=True)
            self.updated.emit()
            signals.calculation_setup_changed.emit()


class CSMethodsModel(PandasModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.current_cs = None
        signals.calculation_setup_selected.connect(self.sync)

    @property
    def methods(self) -> list:
        return self._dataframe.loc[:, "method"].to_list()

    @Slot(str, name="syncModel")
    def sync(self, name: str = None) -> None:
        if name:
            assert name in bw.calculation_setups, "Given calculation setup does not exist."
            self.current_cs = name
            self._dataframe = pd.DataFrame([
                self.build_row(method)
                for method in bw.calculation_setups[self.current_cs].get("ia", [])
            ], columns=self.HEADERS)
        self.updated.emit()

    @staticmethod
    def build_row(method: tuple) -> dict:
        method_metadata = bw.methods[method]
        return {
            "Name": ', '.join(method),
            "Unit": method_metadata.get('unit', "Unknown"),
            "# CFs": method_metadata.get('num_cfs', 0),
            "method": method,
        }

    @Slot(list, name="deleteRows")
    def delete_rows(self, proxies: list) -> None:
        indices = (self.proxy_to_source(p) for p in proxies)
        rows = [i.row() for i in indices]
        self._dataframe = self._dataframe.drop(rows, axis=0).reset_index(drop=True)
        self.updated.emit()
        signals.calculation_setup_changed.emit()  # Trigger update of CS in brightway

    def include_methods(self, new_methods: Iterable) -> None:
        old_methods = set(self.methods)
        data = [self.build_row(m) for m in new_methods if m not in old_methods]
        if data:
            self._dataframe = self._dataframe.append(data, ignore_index=True)
            self.updated.emit()
            signals.calculation_setup_changed.emit()


class ScenarioImportModel(PandasModel):
    HEADERS = ["Scenario name"]

    def sync(self, names: list) -> None:
        self._dataframe = pd.DataFrame(names, columns=self.HEADERS)
        self.updated.emit()
