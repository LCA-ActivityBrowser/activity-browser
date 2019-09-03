# -*- coding: utf-8 -*-
from bw2data.parameters import (ProjectParameter, DatabaseParameter, Group,
                                ActivityParameter)
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

from .delegates import (FloatDelegate, FormulaDelegate, StringDelegate,
                        ViewOnlyDelegate)
from .views import ABDataFrameEdit, dataframe_sync
from ..icons import qicons
from ...signals import signals
from ...bwutils.commontasks import AB_names_to_bw_keys


class BaseExchangeTable(ABDataFrameEdit):
    COLUMNS = []
    # Signal used to correctly control `DetailsGroupBox`
    updated = QtCore.pyqtSignal()

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
            qicons.delete, "Unset formula(s)", None
        )

        self.downstream = False
        self.key = None if not hasattr(parent, "key") else parent.key
        self.exchanges = []
        self._connect_signals()

    def _connect_signals(self):
        signals.database_changed.connect(lambda: self.sync())
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)
        self.remove_formula_action.triggered.connect(self.remove_formula)

    @dataframe_sync
    def sync(self, exchanges=None):
        """ Build the table using either new or stored exchanges iterable.
        """
        if exchanges is not None:
            self.exchanges = exchanges
        self.dataframe = self.build_df()

    def build_df(self) -> pd.DataFrame:
        """ Use the Exchanges Iterable to construct a dataframe.

        Make sure to store the Exchange object itself in the dataframe as well.
        """
        df = pd.DataFrame([
            self.create_row(exchange=exc)[0] for exc in self.exchanges
        ], columns=self.COLUMNS + ["exchange"])
        return df

    def create_row(self, exchange) -> (dict, object):
        """ Take the given Exchange object and extract a number of attributes.
        """
        adj_act = exchange.output if self.downstream else exchange.input
        row = {
            "Amount": exchange.get("amount"),
            "Unit": adj_act.get("unit", "Unknown"),
            "exchange": exchange,
        }
        return row, adj_act

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        """ Get the activity key from the exchange. """
        index = self.get_source_index(proxy)
        exchange = self.dataframe.iloc[index.row(), ]["exchange"]
        return exchange.output if self.downstream else exchange.input

    @QtCore.pyqtSlot()
    def delete_exchanges(self) -> None:
        """ Remove all of the selected exchanges from the activity.
        """
        indexes = [self.get_source_index(p) for p in self.selectedIndexes()]
        rows = [index.row() for index in indexes]
        exchanges = self.dataframe.iloc[rows, ]["exchange"].to_list()
        signals.exchanges_deleted.emit(exchanges)

    def remove_formula(self) -> None:
        """ Remove the formulas for all of the selected exchanges.

        This will also check if the exchange has `original_amount` and
        attempt to overwrite the `amount` with that value after removing the
        `formula` field.

        This can have the additional effect of removing the ActivityParameter
        if it was set for the current activity and all formulas are gone.
        """
        indexes = [self.get_source_index(p) for p in self.selectedIndexes()]
        rows = [index.row() for index in indexes]
        for exchange in self.dataframe.iloc[rows, ]["exchange"]:
            signals.exchange_modified.emit(exchange, "formula", "")

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.exec(a0.globalPos())

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        """ Override the slot which handles data changes in the model.

        Whenever data is changed, call an update to the relevant exchange
        or activity.

        Four possible editable fields:
        Amount, Unit, Product and Formula
        """
        # A single cell was edited.
        if topLeft == bottomRight:
            index = self.get_source_index(topLeft)
            field = AB_names_to_bw_keys[self.dataframe.columns[index.column()]]
            exchange = self.dataframe.iloc[index.row(), ]["exchange"]
            if field in {"amount", "formula"}:
                if field == "amount":
                    value = float(topLeft.data())
                else:
                    value = str(topLeft.data()) if topLeft.data() is not None else ""
                signals.exchange_modified.emit(exchange, field, value)
            else:
                value = str(topLeft.data())
                act_key = exchange.output.key
                signals.activity_modified.emit(act_key, field, value)
        else:
            super().dataChanged(topLeft, bottomRight, roles)

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

    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        """ Be very strict in how double click events work.
        """
        proxy = self.indexAt(e.pos())
        delegate = self.itemDelegateForColumn(proxy.column())

        # If the column we're clicking on is not view-only try and edit
        if not isinstance(delegate, ViewOnlyDelegate):
            self.doubleClicked.emit(proxy)
            # But only edit if the editTriggers contain DoubleClicked
            if self.editTriggers() & self.DoubleClicked:
                self.edit(proxy)
            return

        # No opening anything from the 'product' or 'biosphere' tables
        if self.table_name in {"product", "biosphere"}:
            return

        # Grab the activity key from the exchange and open a tab
        index = self.get_source_index(proxy)
        row = self.dataframe.iloc[index.row(), ]
        key = row["exchange"]["output"] if self.downstream else row["exchange"]["input"]
        signals.open_activity_tab.emit(key)
        signals.add_activity_to_history.emit(key)

    def get_usable_parameters(self) -> list:
        """ Use the `key` set for the table to determine the database and
        group of the activity, using that information to constrain the usable
        parameters.
        """
        project = [
            [p.name, p.amount, "project"] for p in ProjectParameter.select()
        ]
        if self.key is None:
            return project

        query = (DatabaseParameter.select()
                 .where(DatabaseParameter.database == self.key[0]))
        database = [
            [p.name, p.amount, "database"] for p in query.iterator()
        ]

        try:
            # Get the parameter for the current activity
            act = (ActivityParameter
                   .get(ActivityParameter.database == self.key[0],
                        ActivityParameter.code == self.key[1]))
            # First, build a list for parameters in the same group
            query = (ActivityParameter.select()
                     .where(ActivityParameter.group == act.group))
            activity = [
                [p.name, p.amount, "activity"] for p in query.iterator()
            ]
            # Then extend the list with parameters from groups in the `order`
            # field
            group = Group.get(name=act.group)
            query = (ActivityParameter.select()
                     .where(ActivityParameter.group.in_(group.order)))
            activity += [
                [p.name, p.amount, "activity"] for p in query.iterator()
            ]
        except ActivityParameter.DoesNotExist:
            activity = []

        return project + database + activity


class ProductExchangeTable(BaseExchangeTable):
    COLUMNS = ["Amount", "Unit", "Product", "Formula"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, StringDelegate(self))
        self.setItemDelegateForColumn(2, StringDelegate(self))
        self.setItemDelegateForColumn(3, FormulaDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "product"

    def create_row(self, exchange) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Product": adj_act.get("reference product") or adj_act.get("name"),
            "Formula": exchange.get("formula"),
        })
        return row, adj_act

    def _resize(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        self.setColumnHidden(4, True)

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        technosphere exchanges table.
        """
        source = event.source()
        if hasattr(source, "table_name") and source.table_name == "technosphere":
            event.accept()
        elif hasattr(source, "technosphere") and source.technosphere is True:
            event.accept()


class TechnosphereExchangeTable(BaseExchangeTable):
    COLUMNS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database",
        "Uncertainty", "Formula"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(7, FormulaDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "technosphere"
        self.drag_model = True

    def create_row(self, exchange) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Product": adj_act.get("reference product") or adj_act.get("name"),
            "Activity": adj_act.get("name"),
            "Location": adj_act.get("location", "Unknown"),
            "Database": adj_act.get("database"),
            "Uncertainty": adj_act.get("uncertainty type", 0),
            "Formula": exchange.get("formula"),
        })
        return row, adj_act

    def _resize(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        self.setColumnHidden(8, True)

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        downstream exchanges table.
        """
        source = event.source()
        if isinstance(source, DownstreamExchangeTable):
            event.accept()
        elif hasattr(source, "technosphere") and source.technosphere is True:
            event.accept()


class BiosphereExchangeTable(BaseExchangeTable):
    COLUMNS = [
        "Amount", "Unit", "Flow Name", "Compartments", "Database",
        "Uncertainty", "Formula"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(6, FormulaDelegate(self))
        self.table_name = "biosphere"
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)

    def create_row(self, exchange) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Flow Name": adj_act.get("name"),
            "Compartments": " - ".join(adj_act.get('categories', [])),
            "Database": adj_act.get("database"),
            "Uncertainty": adj_act.get("uncertainty type", 0),
            "Formula": exchange.get("formula"),
        })
        return row, adj_act

    def _resize(self) -> None:
        self.setColumnHidden(7, True)

    def dragEnterEvent(self, event):
        """ Only accept exchanges from a technosphere database table
        """
        source = event.source()
        if hasattr(source, "technosphere") and source.technosphere is False:
            event.accept()


class DownstreamExchangeTable(TechnosphereExchangeTable):
    """ Inherit from the `TechnosphereExchangeTable` as the downstream class is
    very similar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # Override the amount column to be a view-only delegate
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.downstream = True
        self.table_name = "downstream"
        self.drag_model = True
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

    def _resize(self) -> None:
        """ Next to `exchange`, also hide the `formula` column.
        """
        self.setColumnHidden(7, True)
        self.setColumnHidden(8, True)

    def contextMenuEvent(self, a0) -> None:
        pass
