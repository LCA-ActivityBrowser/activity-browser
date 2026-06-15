from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt
from loguru import logger

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.calculation_setup import active_flags, ensure_active_lists
from activity_browser.bwutils.commontasks import is_node_product_or_waste
from .cs_table import CSListModel, CSTableView, try_reorder_drop


class FunctionalUnitSection(QtWidgets.QWidget):
    def __init__(self, calculation_setup_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = calculation_setup_name
        self.calculation_setup = bd.calculation_setups.get(self.calculation_setup_name)

        self.view = FunctionalUnitView(self)
        self.model = FunctionalUnitModel(parent=self)
        self.view.setModel(self.model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        try:
            self.calculation_setup = bd.calculation_setups[self.calculation_setup_name]
            df = self.build_df()
            df.reset_index(drop=True, inplace=True)
            self.model.set_dataframe(df)
        except KeyError:
            self.parent().close()
            self.parent().deleteLater()

    def build_df(self):
        keys, amounts = [], []
        cols = ["unit", "name", "product", "location", "database", "processor", "type"]

        for fu in self.calculation_setup.get("inv", []):
            for key, amount in fu.items():
                keys.append(key)
                amounts.append(amount)

        act_df = app.metadata.get_metadata(keys, cols)
        act_df["amount"] = amounts
        act_df["_activity_key"] = keys
        act_df["_active"] = active_flags(self.calculation_setup, "inv")
        act_df["_cs_name"] = self.calculation_setup_name

        act_df["_processor_key"] = act_df["processor"]
        act_df["_processor_key"] = act_df["_processor_key"].fillna(act_df["_activity_key"])

        proc_meta = app.metadata.get_metadata(act_df["_processor_key"].unique(), ["name"])
        act_df["process"] = act_df["_processor_key"].map(proc_meta["name"])

        # Product nodes: metadata "name" is the product; keep process from the processor.
        act_df["product"] = act_df["product"].fillna(act_df["name"])

        act_df.rename({"type": "_type"}, axis="columns", inplace=True)

        cols = ["amount", "unit", "product", "process", "database", "location", "_processor_key", "_activity_key", "_cs_name", "_type", "_active"]

        return act_df[cols].reset_index(drop=True)


class FunctionalUnitView(CSTableView):
    defaultColumnDelegates = {
        "amount": delegates.AmountDelegate
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.ActivityOpen, p.selected_processes(),
                               text="Open process" if len(p.selected_processes()) == 1 else "Open processes",
                               enable=len(p.selected_processes()) > 0
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.CSDeleteFunctionalUnit, p.cs_name(), p.selected_row_indices(),
                               text="Delete Functional Unit" if len(p.selected_processes()) == 1 else "Delete Functional Units",
                               enable=len(p.selected_processes()) > 0
                               ),

        ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def mouseDoubleClickEvent(self, event) -> None:
        """
        Handles the mouse double click event to open the selected activities.

        Args:
            event: The mouse double click event.
        """
        index = self.indexAt(event.pos())
        if index.column() == 1: # Prevent action on amount column
            return super().mouseDoubleClickEvent(event)

        if self.selectedIndexes():
            activities = self.model().values_from_indices("_processor_key", self.selectedIndexes())
            app.actions.ActivityOpen.run(list(set(activities)))

        return None

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            for key in keys:
                if not is_node_product_or_waste(key):
                    keys.remove(key)

            if not keys:
                return

            event.accept()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if try_reorder_drop(self, event):
            return
        if not event.mimeData().hasFormat("application/bw-nodekeylist"):
            super().dropEvent(event)
            return
        event.accept()
        cs_name = self.parent().calculation_setup_name
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        for key in keys.copy():
            if not is_node_product_or_waste(key):
                keys.remove(key)

        app.actions.CSAddFunctionalUnit.run(cs_name, keys)

    def selected_row_indices(self):
        return [i.row() for i in super().selectedIndexes()]
    
    def cs_name(self):
        return self.parent().calculation_setup_name
    
    def selected_processes(self):
        return list(set(self.model().values_from_indices("_processor_key", self.selectedIndexes())))


class FunctionalUnitModel(CSListModel):
    list_key = "inv"
    """
    A model representing the data for the functional units.
    """
    
    def setData(self, index: QtCore.QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole:
            return super().setData(index, value, role)
        if role != Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        if column_name == "amount":
            cs_name = row.get("_cs_name")
            app.actions.CSChangeFunctionalUnit.run(cs_name, index.row(), value)
            return True

        return False
    
    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data (icons) for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data (icon) for the index.
        """
        column_name = self.column_name(index)

        if column_name == "product":
            product_type = self.get(index, "_type")
            if product_type == "waste":
                return icons.qicons.waste
            elif product_type == "processwithreferenceproduct":
                return icons.qicons.processproduct
            else:
                return icons.qicons.product
        elif column_name == "process":
            return icons.qicons.process

        return None
    
    def indexEditable(self, index: QtCore.QModelIndex) -> bool:
        """
        Returns whether the index is editable.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is editable, False otherwise.
        """
        column_name = self.column_name(index)

        if column_name == "amount":
            return True
        
        return False
