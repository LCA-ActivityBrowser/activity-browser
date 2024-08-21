# -*- coding: utf-8 -*-
from typing import List

from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from activity_browser import actions

from ..icons import qicons
from .delegates import *
from .models import (
    BaseExchangeModel,
    BiosphereExchangeModel,
    DownstreamExchangeModel,
    ProductExchangeModel,
    TechnosphereExchangeModel,
)
from .views import ABDataFrameView


class BaseExchangeTable(ABDataFrameView):
    MODEL = BaseExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self._read_only = True

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
        self.properties_action = actions.ExchangeProperties.get_QAction(
            # Use a lambda for the read-only flag, so that the value
            # is not captured at definition, but at execution
            self.selected_exchanges, lambda: self._read_only, self
        )

        self.key = getattr(parent, "key", None)
        self.model = self.MODEL(self.key, self)

        self.downstream = False
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
            | QtWidgets.QAbstractItemView.DoubleClicked
        )
        self._connect_signals()

    def _connect_signals(self):
        self.doubleClicked.connect(lambda: self.model.edit_cell(self.currentIndex()))
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.hide_exchange_columns)

    def hide_exchange_columns(self):
        self.hideColumn(self.model.exchange_column)

    @Slot(name="openActivities")
    def open_activities(self) -> None:
        self.model.open_activities(self.selectedIndexes())

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.exec_(event.globalPos())

    def dragMoveEvent(self, event) -> None:
        """For some reason, this method existing is required for allowing
        dropEvent to occur _everywhere_ in the table.
        """
        pass

    def dropEvent(self, event):
        source_table = event.source()
        keys = source_table.selected_keys()
        event.accept()
        actions.ExchangeNew.run(keys, self.key)

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
    
    def set_read_only(self, read_only: bool):
        if read_only:
            # Clear the selection when read-only is set to false,
            # otherwise the selection persists afterwards
            # and context menu operates on wrong entries
            self.clearSelection()
        self._read_only = read_only

        self.delete_exchange_action.setEnabled(self._read_only)
        self.remove_formula_action.setEnabled(self._read_only)
        self.modify_uncertainty_action.setEnabled(self._read_only)
        self.remove_uncertainty_action.setEnabled(self._read_only)
        if self._read_only:
            self.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
            self.setAcceptDrops(False)
            self.setSelectionMode(self.NoSelection)
        else:
            self.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
            self.setSelectionMode(self.SingleSelection)
            if (
                not self.downstream
            ):  # downstream consumers table never accepts drops
                self.setAcceptDrops(True)


class ProductExchangeTable(BaseExchangeTable):
    MODEL = ProductExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))
        self.setItemDelegateForColumn(3, StringDelegate(self))
        self.setItemDelegateForColumn(4, FormulaDelegate(self))

        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "product"

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.remove_formula_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle("Copy to clipboard")
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)
        menu.addAction(self.properties_action)
        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """Accept exchanges from a technosphere database table, and the
        technosphere exchanges table.
        """
        source = event.source()
        if (
            getattr(source, "table_name", "") == "technosphere"
            or getattr(source, "technosphere", False) is True
        ):
            event.accept()


class TechnosphereExchangeTable(BaseExchangeTable):
    MODEL = TechnosphereExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(13, FormulaDelegate(self))
        self.setItemDelegateForColumn(14, StringDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "technosphere"

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown."""
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column."""
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)
        menu.addAction(self.modify_uncertainty_action)
        menu.addSeparator()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.remove_uncertainty_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle("Copy to clipboard")
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """Accept exchanges from a technosphere database table, and the
        downstream exchanges table.
        """
        source = event.source()
        if getattr(source, "table_name", "") == "downstream" or hasattr(
            source, "technosphere"
        ):
            event.accept()


class BiosphereExchangeTable(BaseExchangeTable):
    MODEL = BiosphereExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyUncertaintyDelegate(self))
        self.setItemDelegateForColumn(12, FormulaDelegate(self))
        self.setItemDelegateForColumn(13, StringDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)
        self.table_name = "biosphere"

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown."""
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column."""
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.modify_uncertainty_action)
        menu.addSeparator()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.remove_uncertainty_action)

        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle("Copy to clipboard")
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """Only accept exchanges from a technosphere database table"""
        if hasattr(event.source(), "technosphere"):
            event.accept()


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
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)
        menu.exec_(event.globalPos())
