# -*- coding: utf-8 -*-
import numbers
from typing import Iterator, Optional

import brightway2 as bw
import pandas as pd
from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Signal, Slot

from activity_browser.signals import signals
from ...widgets import TupleNameDialog
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
        """Call copy on the (first) selected method and present rename dialog.

        TODO: Move to controller
        """
        method = bw.Method(self.get_method(proxy))
        dialog = TupleNameDialog.get_combined_name(
            self.parent(), "Impact category name", "Combined name:", method.name, "Copy"
        )
        if dialog.exec_() == TupleNameDialog.Accepted:
            new_name = dialog.result_tuple
            if new_name in bw.methods:
                warn = "Impact Category with name '{}' already exists!".format(new_name)
                QtWidgets.QMessageBox.warning(self, "Copy failed", warn)
                return
            method.copy(new_name)
            print("Copied method {} into {}".format(str(method.name), str(new_name)))
            signals.new_method.emit(new_name)

    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        if query:
            sorted_names = filter(
                lambda obj: query.lower() in obj[0].lower(), sorted_names
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
    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.cf_column = 0
        self.method: Optional[bw.Method] = None
        self.modified.connect(lambda: self.sync(self.method.name))

    @property
    def uncertain_cols(self) -> list:
        return [self._dataframe.columns.get_loc(c) for c in self.UNCERTAINTY]

    @Slot(name="syncExistingModel")
    @Slot(tuple, name="syncNewModel")
    def sync(self, method: Optional[tuple] = None) -> None:
        if method:
            self.method = bw.Method(method)
        assert self.method is not None, "A method must be set."
        self._dataframe = pd.DataFrame([
            self.build_row(obj) for obj in self.method.load()
        ], columns=self.HEADERS + self.UNCERTAINTY)
        self.cf_column = self._dataframe.columns.get_loc("cf")
        self.updated.emit()

    @classmethod
    def build_row(cls, method_cf) -> dict:
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

    @Slot(QModelIndex, name="modifyCFUncertainty")
    def modify_uncertainty(self, proxy: QModelIndex) -> None:
        """Need to know both keys to select the correct exchange to update

        TODO: Move to controller
        """
        idx = self.proxy_to_source(proxy)
        method_cf = self._dataframe.iat[idx.row(), self.cf_column]
        wizard = UncertaintyWizard(method_cf, self.parent())
        wizard.complete.connect(self.modify_cf)
        wizard.show()

    @Slot(name="removeCFUncertainty")
    def remove_uncertainty(self, proxy_indexes: Iterator[QModelIndex]) -> None:
        """Remove all uncertainty information from the selected CFs.

        NOTE: Does not affect any selected CF that does not have uncertainty
        information.

        TODO: Move to controller
        """
        indices = (
            self.proxy_to_source(p) for p in proxy_indexes
        )
        selected = (
            self._dataframe.iat[idx.row(), self.cf_column] for idx in indices
        )
        modified_cfs = (
            self._unset_uncertainty(cf) for cf in selected
            if isinstance(cf[1], dict)
        )
        cfs = self.method.load()
        for cf in modified_cfs:
            idx = next(i for i, c in enumerate(cfs) if c[0] == cf[0])
            cfs[idx] = cf
        self.method.write(cfs)
        self.modified.emit()

    @staticmethod
    def _unset_uncertainty(cf: tuple) -> tuple:
        """Modifies the given cf to remove the uncertainty dictionary."""
        assert isinstance(cf[1], dict)
        data = [*cf]
        data[1] = data[1].get("amount")
        return tuple(data)

    @Slot(tuple, object, name="modifyCf")
    def modify_cf(self, cf: tuple, uncertainty: dict) -> None:
        """Update the CF with new uncertainty information, possibly converting
        the second item in the tuple to a dictionary without losing information.

        TODO: Move to controller
        """
        data = [*cf]
        if isinstance(data[1], dict):
            data[1].update(uncertainty)
        else:
            uncertainty["amount"] = data[1]
            data[1] = uncertainty
        self.modify_method_with_cf(tuple(data))

    @Slot(tuple, name="modifyMethodWithCf")
    def modify_method_with_cf(self, cf: tuple) -> None:
        """ Take the given CF tuple, add it to the method object stored in
        `self.method` and call .write() & .process() to finalize.

        NOTE: if the flow key matches one of the CFs in method, that CF
        will be edited, if not, a new CF will be added to the method.

        TODO: Move to controller
        """
        cfs = self.method.load()
        idx = next((i for i, c in enumerate(cfs) if c[0] == cf[0]), None)
        if idx is None:
            cfs.append(cf)
        else:
            cfs[idx] = cf
        self.method.write(cfs)
        self.modified.emit()
