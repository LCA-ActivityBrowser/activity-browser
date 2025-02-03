# -*- coding: utf-8 -*-
from typing import List
from logging import getLogger

from qtpy import QtWidgets
from qtpy.QtCore import Slot

import bw2data as bd

from activity_browser import actions

from ..icons import qicons
from .delegates import *
from .inventory import ActivitiesBiosphereTable, ActivitiesBiosphereTree
from .models import (
    BaseExchangeModel,
    BiosphereExchangeModel,
    DownstreamExchangeModel,
    ProductExchangeModel,
    TechnosphereExchangeModel,
)
from .views import ABDataFrameView

log = getLogger(__name__)


class BaseExchangeTable(ABDataFrameView):
    MODEL = BaseExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSelectionMode(BaseExchangeTable.SingleSelection)

        self.delete_exchange_action = actions.ExchangeDelete.get_QAction(
            self.selected_exchanges
        )
        self.remove_formula_action = actions.ExchangeFormulaRemove.get_QAction(
            self.selected_exchanges
        )
        self.modify_uncertainty_action = actions.ExchangeUncertaintyModify.get_QAction(
            self.selected_exchanges
        )
        self.remove_uncertainty_action = actions.ExchangeUncertaintyRemove.get_QAction(
            self.selected_exchanges
        )
        self.copy_exchanges_for_SDF_action = actions.ExchangeCopySDF.get_QAction(
            self.selected_exchanges
        )

        self.key = getattr(parent, "key", None)
        self.model = self.MODEL(self.key, self)
        #
        # self.node_properties_action = actions.NodeProperties.get_QAction(
        #     # Use a lambda for the read-only flag, so that the value
        #     # is not captured at definition, but at execution
        #     self.selected_exchanges, lambda: self.model.is_read_only(), self
        # )

        self.downstream = False
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
            | QtWidgets.QAbstractItemView.DoubleClicked
        )
        self._new_exchange_type = ""
        self._connect_signals()

        if self.model:
            self.setItemDelegateForColumn(self.model.columns.index("Amount"),
                                        FloatDelegate(self))
            self.setItemDelegateForColumn(self.model.columns.index("Unit"),
                                        StringDelegate(self))
            if "Product" in self.model.columns:
                self.setItemDelegateForColumn(self.model.columns.index("Product"),
                                            StringDelegate(self))
            # columns Functional and Allocation factor are set up in the model
            if "Formula" in self.model.columns:
                self.setItemDelegateForColumn(self.model.columns.index("Formula"),
                                            FormulaDelegate(self))
            if "Comment" in self.model.columns:
                self.setItemDelegateForColumn(self.model.columns.index("Comment"),
                                            StringDelegate(self))
            if "Uncertainty" in self.model.columns:
                self.setItemDelegateForColumn(self.model.columns.index("Uncertainty"),
                                            ViewOnlyUncertaintyDelegate(self))


    def _connect_signals(self):
        self.doubleClicked.connect(lambda: self.model.edit_cell(self.currentIndex()))
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.hide_exchange_columns)

    def hide_exchange_columns(self):
        self.hideColumn(self.model.exchange_column)

    @Slot(name="openActivities")
    def open_activities(self) -> None:
        self.model.open_activities(self.selectedIndexes())

    def contextMenuEvent(self, event, show_uncertainty: bool = True) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()

        menu.addAction(qicons.right, "Open processes", self.open_activities)
        if show_uncertainty:
            menu.addAction(self.modify_uncertainty_action)
        menu.addAction(self.node_properties_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle("Copy to clipboard")
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)
        menu.addSeparator()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        if show_uncertainty:
            menu.addAction(self.remove_uncertainty_action)

        menu.exec_(event.globalPos())

    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            for key in keys:
                act = bd.get_node(key=key)
                if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                    keys.remove(key)

            if not keys:
                return

            event.accept()

    def dropEvent(self, event):
        event.accept()
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                keys.remove(key)

        actions.ExchangeNew.run(keys, self.key, self._new_exchange_type)

    def get_usable_parameters(self):
        return self.model.get_usable_parameters()

    def get_interpreter(self):
        return self.model.get_interpreter()

    def selected_exchanges(self) -> List[any]:
        # The context menu still makes sense in read-only mode, but
        # item selection is disabled, so we need to use the current item
        if self.selectedIndexes():
            return [self.model.get_exchange(index) for index in self.selectedIndexes()]
        else:
            return [self.model.get_exchange(self.currentIndex())]

    def set_read_only_flag(self, read_only: bool):
        self._read_only = read_only

        self.model.set_read_only(read_only)
        self.delete_exchange_action.setEnabled(not self._read_only)
        self.remove_formula_action.setEnabled(not self._read_only)
        self.modify_uncertainty_action.setEnabled(not self._read_only)
        self.remove_uncertainty_action.setEnabled(not self._read_only)
        if self._read_only:
            self.setAcceptDrops(False)
        else:
            if (
                not self.downstream
            ):  # downstream consumers table never accepts drops
                self.setAcceptDrops(True)

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns."""
        if self.model and "Uncertainty" in self.model.columns:
            cols = self.model.columns
            self.setColumnHidden(cols.index("Uncertainty"), not show)
            self.setColumnHidden(cols.index("pedigree"), not show)
            for c in self.model.UNCERTAINTY_ITEMS:
                self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column."""
        if self.model and "Comment" in self.model.columns:
            cols = self.model.columns
            self.setColumnHidden(cols.index("Comment"), not show)


class ProductExchangeTable(BaseExchangeTable):
    MODEL = ProductExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "product"
        self._new_exchange_type = "technosphere"

    def contextMenuEvent(self, event, show_uncertainty: bool = True) -> None:
        if self.indexAt(event.pos()).row() != -1:
            return super().contextMenuEvent(event, show_uncertainty)

        menu = QtWidgets.QMenu(self)
        product_action = actions.ActivityNewProduct.get_QAction(self.key)
        menu.addAction(product_action)

        menu.exec_(event.globalPos())


class TechnosphereExchangeTable(BaseExchangeTable):
    MODEL = TechnosphereExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "technosphere"
        self._new_exchange_type = "technosphere"


class BiosphereExchangeTable(BaseExchangeTable):
    MODEL = BiosphereExchangeModel
    biosphere_nodes = ["emission", "natural resource", "inventory indicator", "economic"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.table_name = "biosphere"
        self._new_exchange_type = "biosphere"

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            for key in keys:
                act = bd.get_node(key=key)
                if act["type"] not in self.biosphere_nodes:
                    keys.remove(key)

            if not keys:
                return

            event.accept()

    def dropEvent(self, event):
        event.accept()
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in self.biosphere_nodes:
                keys.remove(key)

        actions.ExchangeNew.run(keys, self.key, self._new_exchange_type)


class DownstreamExchangeTable(BaseExchangeTable):
    """Downstream table class is very similar to technosphere table, just more
    restricted.
    """

    MODEL = DownstreamExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)
        self.downstream = True
        self.table_name = "downstream"

    def contextMenuEvent(self, event) -> None:
        super().contextMenuEvent(event, show_uncertainty = False)
