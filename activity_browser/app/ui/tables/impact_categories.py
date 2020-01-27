# -*- coding: utf-8 -*-
import numbers
from typing import Iterable, Optional

import brightway2 as bw
from pandas import DataFrame
from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Signal, Slot

from ...signals import signals
from ..icons import qicons
from ..widgets import TupleNameDialog
from ..wizards import UncertaintyWizard
from .views import ABDataFrameView, dataframe_sync
from .delegates import FloatDelegate, UncertaintyDelegate


class MethodsTable(ABDataFrameView):
    HEADERS = ["Name", "Unit", "# CFs", "method"]
    new_method = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_model = True
        self.method_col = 0
        self.setDragEnabled(True)
        self.setDragDropMode(ABDataFrameView.DragOnly)
        self.sync()
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(self.method_selected)
        signals.project_selected.connect(self.sync)

    def get_method(self, proxy: QModelIndex) -> tuple:
        index = self.get_source_index(proxy)
        return self.dataframe.iat[index.row(), self.method_col]

    @Slot(QModelIndex, name="methodSelection")
    def method_selected(self, proxy):
        signals.method_selected.emit(self.get_method(proxy))

    def selected_methods(self) -> Iterable:
        """Returns a generator which yields the 'method' for each row."""
        return (self.get_method(p) for p in self.selectedIndexes())

    @dataframe_sync
    @Slot(name="syncTable")
    def sync(self, query=None) -> None:
        sorted_names = sorted([(", ".join(method), method) for method in bw.methods])
        if query:
            sorted_names = filter(
                lambda obj: query.lower() in obj[0].lower(), sorted_names
            )
        self.dataframe = DataFrame([
            self.build_row(method_obj) for method_obj in sorted_names
        ], columns=self.HEADERS)
        self.method_col = self.dataframe.columns.get_loc("method")

    def build_row(self, method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }

    def _resize(self) -> None:
        self.setColumnHidden(self.method_col, True)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(qicons.copy, "Duplicate Impact Category", self.copy_method)
        menu.exec_(event.globalPos())

    @Slot(name="copyMethod")
    def copy_method(self) -> None:
        """Call copy on the (first) selected method and present rename dialog."""
        method = bw.Method(self.get_method(next(p for p in self.selectedIndexes())))
        dialog = TupleNameDialog.get_combined_name(
            self, "Impact category name", "Combined name:", method.name, "Copy"
        )
        if dialog.exec_() == TupleNameDialog.Accepted:
            new_name = dialog.result_tuple
            if new_name in bw.methods:
                warn = "Impact Category with name '{}' already exists!".format(new_name)
                QtWidgets.QMessageBox.warning(self, "Copy failed", warn)
                return
            method.copy(new_name)
            print("Copied method {} into {}".format(str(method.name), str(new_name)))
            self.new_method.emit(new_name)


class CFTable(ABDataFrameView):
    COLUMNS = ["name", "categories", "amount", "unit", "uncertain"]
    HEADERS = ["Name", "Category", "Amount", "Unit", "Uncertain"] + ["cf"]
    UNCERTAINTY = [
        "uncertainty type", "loc", "scale", "shape", "minimum", "maximum"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cf_column = None
        self.method: Optional[bw.Method] = None
        self.wizard: Optional[UncertaintyWizard] = None
        self.setVisible(False)
        self.setItemDelegateForColumn(6, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.setItemDelegateForColumn(11, FloatDelegate(self))

    @dataframe_sync
    def sync(self, method: tuple) -> None:
        self.method = bw.Method(method)
        self.dataframe = DataFrame([
            self.build_row(obj) for obj in self.method.load()
        ], columns=self.HEADERS + self.UNCERTAINTY)
        self.cf_column = self.dataframe.columns.get_loc("cf")

    def build_row(self, method_cf) -> dict:
        key, amount = method_cf[:2]
        flow = bw.get_activity(key)
        row = {
            self.HEADERS[i]: flow.get(c) for i, c in enumerate(self.COLUMNS)
        }
        # If uncertain, unpack the uncertainty dictionary
        uncertain = not isinstance(amount, numbers.Number)
        if uncertain:
            row.update({k: amount.get(k, "nan") for k in self.UNCERTAINTY})
            amount = amount["amount"]
        row.update({"Amount": amount, "Uncertain": uncertain, "cf": method_cf})
        return row

    def _resize(self) -> None:
        self.setColumnHidden(5, True)
        self.hide_uncertain()
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
        ))

    @Slot(bool, name="toggleUncertainColumns")
    def hide_uncertain(self, hide: bool = True) -> None:
        for c in self.UNCERTAINTY:
            self.setColumnHidden(self.dataframe.columns.get_loc(c), hide)

    def contextMenuEvent(self, event) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addAction(qicons.edit, "Modify uncertainty", self.modify_uncertainty)
        menu.exec_(event.globalPos())

    @Slot(name="modifyCFUncertainty")
    def modify_uncertainty(self) -> None:
        """Need to know both keys to select the correct exchange to update"""
        index = self.get_source_index(next(p for p in self.selectedIndexes()))
        method_cf = self.dataframe.iat[index.row(), self.cf_column]
        self.wizard = UncertaintyWizard(method_cf, self)
        self.wizard.complete.connect(self.modify_cf)
        self.wizard.show()

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
        self.modify_method_with_cf(tuple(data))

    @Slot(tuple, name="modifyMethodWithCf")
    def modify_method_with_cf(self, cf: tuple) -> None:
        """ Take the given CF tuple, add it to the method object stored in
        `self.method` and call .write() & .process() to finalize.

        NOTE: if the flow key matches one of the CFs in method, that CF
        will be edited, if not, a new CF will be added to the method.
        """
        cfs = self.method.load()
        idx = next((i for i, c in enumerate(cfs) if c[0] == cf[0]), None)
        if idx is None:
            cfs.append(cf)
        else:
            cfs[idx] = cf
        self.method.write(cfs)
        self.sync(self.method.name)
