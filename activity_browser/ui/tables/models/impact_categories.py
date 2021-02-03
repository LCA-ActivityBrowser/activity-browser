# -*- coding: utf-8 -*-
import brightway2 as bw
import pandas as pd
from PySide2 import QtWidgets
from PySide2.QtCore import QModelIndex, Slot, Qt

from activity_browser.signals import signals
from ...widgets import TupleNameDialog
from .base import PandasModel


class MethodsListModel(PandasModel):
    HEADERS = ["Name", "Unit", "# CFs", "method"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.method_col = 0

    def get_method(self, proxy: QModelIndex) -> tuple:
        proxy_model = proxy.model()
        idx = proxy_model.mapToSource(proxy)
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
        self.refresh_model()

    @staticmethod
    def build_row(method_obj) -> dict:
        method = bw.methods[method_obj[1]]
        return {
            "Name": method_obj[0],
            "Unit": method.get("unit", "Unknown"),
            "# CFs": str(method.get("num_cfs", 0)),
            "method": method_obj[1],
        }

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled
