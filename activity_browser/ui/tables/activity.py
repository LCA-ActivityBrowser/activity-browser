# -*- coding: utf-8 -*-
from PySide2 import QtWidgets
from PySide2.QtCore import Slot

from .delegates import *
from .models import (
    BaseExchangeModel, ProductExchangeModel, TechnosphereExchangeModel,
    BiosphereExchangeModel, DownstreamExchangeModel,
)
from .views import ABDataFrameView
from ..icons import qicons
from ...signals import signals


class BaseExchangeTable(ABDataFrameView):
    MODEL = BaseExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum)
        )

        self.delete_exchange_action = QtWidgets.QAction(
            qicons.delete, "Delete exchange(s)", None
        )
        self.remove_formula_action = QtWidgets.QAction(
            qicons.delete, "Clear formula(s)", None
        )
        self.modify_uncertainty_action = QtWidgets.QAction(
            qicons.edit, "Modify uncertainty", None
        )
        self.remove_uncertainty_action = QtWidgets.QAction(
            qicons.delete, "Remove uncertainty/-ies", None
        )
        self.copy_exchanges_for_SDF_action = QtWidgets.QAction(
            qicons.superstructure, "Exchanges for scenario difference file", None
        )
        self.key = getattr(parent, "key", None)
        self.model = self.MODEL(self.key, self)
        self.downstream = False
        self._connect_signals()

    def _connect_signals(self):
        self.delete_exchange_action.triggered.connect(
            lambda: self.model.delete_exchanges(self.selectedIndexes())
        )
        self.remove_formula_action.triggered.connect(
            lambda: self.model.remove_formula(self.selectedIndexes())
        )
        self.modify_uncertainty_action.triggered.connect(
            lambda: self.model.modify_uncertainty(self.currentIndex())
        )
        self.remove_uncertainty_action.triggered.connect(
            lambda: self.model.remove_uncertainty(self.selectedIndexes())
        )
        self.copy_exchanges_for_SDF_action.triggered.connect(
            lambda: self.model.copy_exchanges_for_SDF(self.selectedIndexes())
        )
        self.model.updated.connect(self.update_proxy_model)
        self.model.updated.connect(self.custom_view_sizing)


    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        super().custom_view_sizing()
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.setColumnHidden(self.model.exchange_column, True)

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
        """ For some reason, this method existing is required for allowing
        dropEvent to occur _everywhere_ in the table.
        """
        pass

    def dropEvent(self, event):
        source_table = event.source()
        keys = [source_table.get_key(i) for i in source_table.selectedIndexes()]
        event.accept()
        signals.exchanges_add.emit(keys, self.key)

    def get_usable_parameters(self):
        return self.model.get_usable_parameters()

    def get_interpreter(self):
        return self.model.get_interpreter()


class ProductExchangeTable(BaseExchangeTable):
    MODEL = ProductExchangeModel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))
        self.setItemDelegateForColumn(3, FormulaDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "product"

    def contextMenuEvent(self, event) -> None:
        if self.indexAt(event.pos()).row() == -1:
            return
        menu = QtWidgets.QMenu()
        menu.addAction(self.remove_formula_action)
        # Submenu copy to clipboard
        submenu_copy = QtWidgets.QMenu(menu)
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        technosphere exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "technosphere" or
                getattr(source, "technosphere", False) is True):
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

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        super().custom_view_sizing()
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)
        super().custom_view_sizing()

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
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        downstream exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "downstream" or
                hasattr(source, "technosphere")):
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

    @Slot(name="resizeView")
    def custom_view_sizing(self) -> None:
        super().custom_view_sizing()
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.model.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def show_comments(self, show: bool = False) -> None:
        """Show or hide the comment column.
        """
        cols = self.model.columns
        self.setColumnHidden(cols.index("Comment"), not show)
        super().custom_view_sizing()

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
        submenu_copy.setTitle('Copy to clipboard')
        submenu_copy.setIcon(qicons.copy_to_clipboard)
        submenu_copy.addAction(self.copy_exchanges_for_SDF_action)
        menu.addMenu(submenu_copy)

        menu.exec_(event.globalPos())

    def dragEnterEvent(self, event):
        """ Only accept exchanges from a technosphere database table
        """
        if hasattr(event.source(), "technosphere"):
            event.accept()


class DownstreamExchangeTable(BaseExchangeTable):
    """ Downstream table class is very similar to technosphere table, just more
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
