# -*- coding: utf-8 -*-
import numbers
from typing import Iterator, Optional

import brightway2 as bw
import pandas as pd
from PySide2.QtCore import QModelIndex, Slot

from activity_browser.signals import signals
from ...wizards import UncertaintyWizard
from .base import PandasModel, DragPandasModel


class MethodsListModel(DragPandasModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.method_col = 0
        signals.project_selected.connect(self.sync)

    def get_method(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.method_col]

    @Slot(QModelIndex, name="copyMethod")
    def copy_method(self, proxy: QModelIndex) -> None:
        method = self.get_method(proxy)
        signals.copy_method.emit(method)

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        if query:
            sorted_names = (
                m for m in sorted_names if query.lower() in m[0].lower()
            )
        self._dataframe = pd.DataFrame([
            self.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)
        self.method_col = self._dataframe.columns.get_loc("method")
        self.updated.emit()

    @staticmethod
    def build_row(method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }


class CFModel(PandasModel):
    COLUMNS = ["name", "categories", "amount", "unit"]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertainty"] + ["cf"]
    UNCERTAINTY = ["loc", "scale", "shape", "minimum", "maximum"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.cf_column = 0
        self.method: Optional[bw.Method] = None
        signals.method_modified.connect(self.sync)

    @property
    def uncertain_cols(self) -> list:
        return [self._dataframe.columns.get_loc(c) for c in self.UNCERTAINTY]

    @Slot(name="syncExistingModel")
    @Slot(tuple, name="syncNewModel")
    def sync(self, method: Optional[tuple] = None) -> None:
        if self.method and self.method.name != method:
            return
        if method:
            self.method = bw.Method(method)
        assert self.method is not None, "A method must be set."
        self._dataframe = pd.DataFrame([
            self.build_row(obj) for obj in self.method.load()
        ], columns=self.HEADERS + self.UNCERTAINTY)
        self.cf_column = self._dataframe.columns.get_loc("cf")
        self.updated.emit()

    @classmethod
    def build_row(cls, method_cf: tuple) -> dict:
        key, amount = method_cf[:2]
        flow = bw.get_activity(key)
        row = {
            cls.HEADERS[i]: flow.get(c) for i, c in enumerate(cls.COLUMNS)
        }
        # If uncertain, unpack the uncertainty dictionary
        uncertain = not isinstance(amount, numbers.Number)
        if uncertain:
            row.update({k: amount.get(k, "nan") for k in cls.UNCERTAINTY})
            uncertain = amount.get("uncertainty type")
            amount = amount["amount"]
        else:
            uncertain = 0
        row.update({"Amount": amount, "Uncertainty": uncertain, "cf": method_cf})
        return row

    def get_cf(self, proxy: QModelIndex) -> tuple:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.cf_column]

    @Slot(QModelIndex, name="modifyCFUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        """Need to know both keys to select the correct exchange to update."""
        method_cf = self.get_cf(proxy)
        wizard = UncertaintyWizard(method_cf, self.parent())
        wizard.complete.connect(self.modify_cf)
        wizard.show()

    @Slot(list, name="removeCFUncertainty")
    def remove_uncertainty(self, proxy_indexes: Iterator[QModelIndex]) -> None:
        to_be_modified = [self.get_cf(p) for p in proxy_indexes]
        signals.remove_cf_uncertainties.emit(to_be_modified, self.method.name)

    @Slot(tuple, object, name="modifyCf")
    def modify_cf(self, cf: tuple, uncertainty: dict) -> None:
        """Update the CF with new uncertainty information, possibly converting
        the second item in the tuple to a dictionary without losing information.
        """
        data = [*cf]
        if isinstance(data[1], dict):
            data[1].update(uncertainty)
        else:
            uncertainty["amount"] = data[1]
            data[1] = uncertainty
        signals.edit_method_cf.emit(tuple(data), self.method.name)
