from typing import Iterable

import numpy as np
import pandas as pd
from PySide2.QtCore import QModelIndex, Qt, Slot

from activity_browser import log, signals
from activity_browser.bwutils import commontasks as bc
from activity_browser.mod import bw2data as bd
from activity_browser.mod.bw2data.backends import ActivityDataset

from .base import EditablePandasModel, PandasModel


class CSGenericModel(EditablePandasModel):
    """Intermediate class to enable internal move functionality for the
    reference flows and impact categories tables. The below flags and relocate functions
    are required to enable internal move.

    Technically, CSMethodsModel is not editable, but as no editing delegates are set in the
    tables, no editing is possible.
    """

    def flags(self, index):
        """Returns flags"""
        if not index.isValid():
            return super().flags(index) | Qt.ItemIsDropEnabled
        if index.row() < len(self._dataframe):
            return super().flags(index) | Qt.ItemIsDragEnabled
        return super().flags(index)

    def relocateRow(self, row_source, row_target) -> None:
        """Relocate a row.
        Move a row in the table to another position and store the new dataframe
        """
        row_a, row_b = max(row_source, row_target), min(row_source, row_target)
        self.beginMoveRows(QModelIndex(), row_a, row_a, QModelIndex(), row_b)
        # copy data
        data_source = self._dataframe.iloc[row_source].copy()
        if row_source > row_target:  # the row needs to be moved up
            pass
            # delete old row
            self._dataframe = self._dataframe.drop(row_source, axis=0).reset_index(
                drop=True
            )
            # insert data
            self._dataframe = pd.DataFrame(
                np.insert(
                    self._dataframe.values, row_target, values=data_source, axis=0
                ),
                columns=self.HEADERS,
            )
        elif row_source < row_target:  # the row needs to be moved down
            pass
            # insert data
            self._dataframe = pd.DataFrame(
                np.insert(
                    self._dataframe.values, row_target, values=data_source, axis=0
                ),
                columns=self.HEADERS,
            )
            # delete old row
            self._dataframe = self._dataframe.drop(row_source, axis=0).reset_index(
                drop=True
            )

        self.updated.emit()
        signals.calculation_setup_changed.emit()
        self.endMoveRows()


class CSActivityModel(CSGenericModel):
    HEADERS = ["Amount", "Unit", "Product", "Activity", "Location", "Database"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.current_cs = None
        self.key_col = 0
        self._activities = {}

        self.HEADERS = self.HEADERS + ["key"]

        signals.calculation_setup_selected.connect(self.load)
        self.dataChanged.connect(lambda: signals.calculation_setup_changed.emit())

    @property
    def activities(self) -> list:
        # if no dataframe is present return empty list
        if not isinstance(self._dataframe, pd.DataFrame):
            return []
        # else return the selected activities
        selection = self._dataframe.loc[:, ["Amount", "key"]].to_dict(orient="records")
        return [{x["key"]: x["Amount"]} for x in selection]

    def get_key(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.key_col]

    def load(self, cs_name: str = None):

        for act in self._activities.values():
            act.changed.disconnect(self.sync)
        self._activities.clear()

        self.current_cs = cs_name

        if not cs_name:
            return

        self.sync()

    def sync(self):
        assert self.current_cs, "CS Model not yet loaded"
        fus = bd.calculation_setups.get(self.current_cs, {}).get("inv", [])
        df = pd.DataFrame(
            [
                self.build_row(key, amount)
                for func_unit in fus
                for key, amount in func_unit.items()
            ],
            columns=self.HEADERS,
        )
        # Drop rows where the fu key was invalid in some way.
        self._dataframe = df.dropna().reset_index(drop=True)
        self.key_col = self._dataframe.columns.get_loc("key")
        self.updated.emit()

    def build_row(self, key: tuple, amount: float = 1.0) -> dict:
        try:
            act = bd.get_activity(key)
            if act.get("type", "process") != "process":
                raise TypeError("Activity is not of type 'process'")
            row = {
                key: act.get(bc.AB_names_to_bw_keys[key], "")
                for key in self.HEADERS[:-1]
            }
            row.update({"Amount": amount, "key": key})

            act.changed.connect(self.sync, Qt.UniqueConnection)
            self._activities[act.key] = act

            return row
        except (TypeError, ActivityDataset.DoesNotExist):
            log.error(
                f"Could not load key '{key}' in Calculation Setup '{self.current_cs}'"
            )
            return {}

    @Slot(name="deleteRows")
    def delete_rows(self, proxies: list) -> None:
        """Delete one or more activities from the Reference flows table"""
        indices = (self.proxy_to_source(p) for p in proxies)
        rows = {i.row() for i in indices}

        # we can disconnect from the deleted activities
        for key in [self._dataframe.at[row, "key"] for row in rows]:
            activity = bd.get_activity(key)
            activity.changed.disconnect(self.sync)
            del self._activities[activity.key]

        self._dataframe = self._dataframe.drop(rows).reset_index(drop=True)
        self.updated.emit()
        signals.calculation_setup_changed.emit()  # Trigger update of CS in brightway

    def include_activities(self, new_activities: Iterable) -> None:
        existing = set(self._dataframe.loc[:, "key"])
        data = []
        for fu in (f for f in new_activities if existing.isdisjoint(f)):
            k, v = zip(*fu.items())
            data.append(self.build_row(k[0], v[0]))
        if data:
            self._dataframe = pd.concat(
                [self._dataframe, pd.DataFrame(data)], ignore_index=True
            )
            self.updated.emit()
            signals.calculation_setup_changed.emit()


class CSMethodsModel(CSGenericModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.current_cs = None
        self._methods = {}

        signals.calculation_setup_selected.connect(self.load)

    @property
    def methods(self) -> list:
        return (
            []
            if self._dataframe is None
            else self._dataframe.loc[:, "method"].to_list()
        )

    def load(self, cs_name: str = None) -> None:
        """
        Load a calculation setup defined by cs_name into the methods table.
        """
        # disconnect from all the previous methods so any virtual methods delete if appropriate
        for method in self._methods.values():
            method.changed.disconnect(self.sync)
        self._methods.clear()

        # set the provided cs as current and synchronize our data
        self.current_cs = cs_name

        if not cs_name:
            return

        self.sync()

    def sync(self) -> None:
        """
        Synchronize the methods table for the current calculation setup. Any methods that are not present in
        the cs_controller will be omitted.
        """
        assert self.current_cs, "CS Model not yet loaded"

        # collect all method tuples from calculation setup that are also actually available
        method_tuples = [
            mthd
            for mthd in bd.calculation_setups[self.current_cs].get("ia", [])
            if mthd in bd.methods
        ]

        # build rows for all the collected methods and store in our dataframe
        self._dataframe = pd.DataFrame(
            [self.build_row(mthd) for mthd in method_tuples], columns=self.HEADERS
        )

        self.updated.emit()

    def build_row(self, method_tuple: tuple) -> dict:
        """
        Build a single row for the methods table and connect the table to the method we're building the row for.
        """
        # gather data using the given method_tuple
        method_metadata = bd.methods[method_tuple]
        method = bd.Method(method_tuple)

        # construct a row dictionary
        row = {
            "Name": ", ".join(method_tuple),
            "Unit": method_metadata.get("unit", "Unknown"),
            "# CFs": method_metadata.get("num_cfs", 0),
            "method": method_tuple,
        }

        # if the method changes we need to sync
        method.changed.connect(self.sync, Qt.UniqueConnection)
        self._methods[method.name] = method

        return row

    @Slot(list, name="deleteRows")
    def delete_rows(self, proxies: list) -> None:
        """Delete one or more methods from the Impact categories table"""
        indices = (self.proxy_to_source(p) for p in proxies)
        rows = {i.row() for i in indices}

        # we can disconnect from the deleted methods
        for method_tuple in [self._dataframe.at[row, "method"] for row in rows]:
            method = bd.Method(method_tuple)
            method.changed.disconnect(self.sync)
            del self._methods[method.name]

        self._dataframe = self._dataframe.drop(rows).reset_index(drop=True)
        self.updated.emit()
        signals.calculation_setup_changed.emit()  # Trigger update of CS in brightway

    def include_methods(self, new_methods: Iterable) -> None:
        old_methods = set(self.methods)
        data = [self.build_row(m) for m in new_methods if m not in old_methods]
        if data:
            self._dataframe = pd.concat(
                [self._dataframe, pd.DataFrame(data)], ignore_index=True
            )
            self.updated.emit()
            signals.calculation_setup_changed.emit()


class ScenarioImportModel(PandasModel):
    HEADERS = ["Scenario name"]

    def sync(self, names: list) -> None:
        self._dataframe = pd.DataFrame(names, columns=self.HEADERS)
        self.updated.emit()
