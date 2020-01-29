# -*- coding: utf-8 -*-
import itertools

from asteval import Interpreter
from bw2data.parameters import (ProjectParameter, DatabaseParameter, Group,
                                ActivityParameter)
from bw2data.proxies import ExchangeProxyBase
import pandas as pd
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Signal, Slot

from .delegates import (FloatDelegate, FormulaDelegate, StringDelegate,
                        UncertaintyDelegate, ViewOnlyDelegate)
from .views import ABDataFrameEdit, dataframe_sync
from ..icons import qicons
from ..wizards import UncertaintyWizard
from ...signals import signals
from ...bwutils import PedigreeMatrix
from ...bwutils.commontasks import AB_names_to_bw_keys


class BaseExchangeTable(ABDataFrameEdit):
    COLUMNS = []
    # Signal used to correctly control `DetailsGroupBox`
    updated = Signal()
    # Fields accepted by brightway to be stored in exchange objects.
    VALID_FIELDS = {
        "amount", "formula", "uncertainty type", "loc", "scale", "shape",
        "minimum", "maximum"
    }

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

        self.downstream = False
        self.key = None if not hasattr(parent, "key") else parent.key
        self.exchanges = []
        self.exchange_column = 0
        self._connect_signals()

    def _connect_signals(self):
        self.delete_exchange_action.triggered.connect(self.delete_exchanges)
        self.remove_formula_action.triggered.connect(self.remove_formula)
        self.modify_uncertainty_action.triggered.connect(self.modify_uncertainty)

    @dataframe_sync
    def sync(self, exchanges=None):
        """ Build the table using either new or stored exchanges iterable.
        """
        if exchanges is not None:
            self.exchanges = exchanges
        self.dataframe = self.build_df()

    @property
    def df_columns(self) -> list:
        return self.COLUMNS + ["exchange"]

    def build_df(self) -> pd.DataFrame:
        """ Use the Exchanges Iterable to construct a dataframe.

        Make sure to store the Exchange object itself in the dataframe as well.
        """
        columns = self.df_columns
        df = pd.DataFrame([
            self.create_row(exchange=exc)[0] for exc in self.exchanges
        ], columns=columns)
        self.exchange_column = columns.index("exchange")
        return df

    def create_row(self, exchange) -> (dict, object):
        """ Take the given Exchange object and extract a number of attributes.
        """
        adj_act = exchange.output if self.downstream else exchange.input
        row = {
            "Amount": float(exchange.get("amount", 1)),
            "Unit": adj_act.get("unit", "Unknown"),
            "exchange": exchange,
        }
        return row, adj_act

    def get_key(self, proxy: QtCore.QModelIndex) -> tuple:
        """ Get the activity key from an exchange.

        This is done by reaching into the table model through the proxy model
        """
        index = self.get_source_index(proxy)
        exchange = self.model.index(index.row(), self.exchange_column).data()
        act = exchange.output if self.downstream else exchange.input
        return act.key

    def open_activities(self) -> None:
        """ Take the selected indexes and attempt to open activity tabs.
        """
        for proxy in self.selectedIndexes():
            act = self.get_key(proxy)
            signals.open_activity_tab.emit(act)
            signals.add_activity_to_history.emit(act)

    @Slot()
    def delete_exchanges(self) -> None:
        """ Remove all of the selected exchanges from the activity.
        """
        indexes = (self.get_source_index(p) for p in self.selectedIndexes())
        exchanges = [
            self.model.index(index.row(), self.exchange_column).data()
            for index in indexes
        ]
        signals.exchanges_deleted.emit(exchanges)

    def remove_formula(self) -> None:
        """ Remove the formulas for all of the selected exchanges.

        This will also check if the exchange has `original_amount` and
        attempt to overwrite the `amount` with that value after removing the
        `formula` field.
        """
        indexes = (self.get_source_index(p) for p in self.selectedIndexes())
        exchanges = [
            self.model.index(index.row(), self.exchange_column).data()
            for index in indexes
        ]
        for exchange in exchanges:
            signals.exchange_modified.emit(exchange, "formula", "")

        # Clear out all ParameterizedExchanges before recalculating
        param = ActivityParameter.get_or_none(database=self.key[0], code=self.key[1])
        if param:
            signals.exchange_formula_changed.emit(self.key)

    @Slot(name="modifyExchangeUncertainty")
    def modify_uncertainty(self) -> None:
        """Need to know both keys to select the correct exchange to update"""
        index = self.get_source_index(next(p for p in self.selectedIndexes()))
        exchange = self.model.index(index.row(), self.exchange_column).data()
        wizard = UncertaintyWizard(exchange, self)
        wizard.show()

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.exec_(a0.globalPos())

    def dataChanged(self, topLeft, bottomRight, roles=None) -> None:
        """ Override the slot which handles data changes in the model.

        Whenever data is changed, call an update to the relevant exchange
        or activity.

        Four possible editable fields:
        Amount, Unit, Product and Formula
        """
        # A single cell was edited.
        if topLeft == bottomRight and topLeft.isValid():
            index = self.get_source_index(topLeft)
            header = self.model.headerData(index.column(), QtCore.Qt.Horizontal)
            field = AB_names_to_bw_keys.get(header, header)
            exchange = self.model.index(index.row(), self.exchange_column).data()
            if field in self.VALID_FIELDS:
                value = topLeft.data() if topLeft.data() is not None else ""
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

    def get_usable_parameters(self):
        """ Use the `key` set for the table to determine the database and
        group of the activity, using that information to constrain the usable
        parameters.
        """
        project = (
            [k, v, "project"] for k, v in ProjectParameter.static().items()
        )
        if self.key is None:
            return project

        database = (
            [k, v, "database"]
            for k, v in DatabaseParameter.static(self.key[0]).items()
        )

        # Determine if the activity is already part of a parameter group.
        query = (Group.select()
                 .join(ActivityParameter, on=(Group.name == ActivityParameter.group))
                 .where(ActivityParameter.database == self.key[0],
                        ActivityParameter.code == self.key[1])
                 .distinct())
        if query.exists():
            group = query.get()
            # First, build a list for parameters in the same group
            activity = (
                [p.name, p.amount, "activity"]
                for p in ActivityParameter.select().where(ActivityParameter.group == group.name)
            )
            # Then extend the list with parameters from groups in the `order`
            # field
            additions = (
                [p.name, p.amount, "activity"]
                for p in ActivityParameter.select().where(ActivityParameter.group << group.order)
            )
            activity = itertools.chain(activity, additions)
        else:
            activity = []

        return itertools.chain(project, database, activity)

    def get_interpreter(self) -> Interpreter:
        """ Use the activity key to determine which symbols are added
        to the formula interpreter.
        """
        interpreter = Interpreter()
        act = ActivityParameter.get_or_none(database=self.key[0], code=self.key[1])
        if act:
            interpreter.symtable.update(ActivityParameter.static(act.group, full=True))
        else:
            print("No parameter found for {}, creating one on formula save".format(self.key))
            interpreter.symtable.update(ProjectParameter.static())
            interpreter.symtable.update(DatabaseParameter.static(self.key[0]))
        return interpreter


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
        self.setColumnHidden(self.exchange_column, True)

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(self.remove_formula_action)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        technosphere exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "technosphere" or
                getattr(source, "technosphere", False) is True):
            event.accept()


class TechnosphereExchangeTable(BaseExchangeTable):
    COLUMNS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database",
        "Uncertainty", "Formula"
    ]
    UNCERTAINTY = [
        "loc", "scale", "shape", "minimum", "maximum"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(6, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(7, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.setItemDelegateForColumn(11, FloatDelegate(self))
        self.setItemDelegateForColumn(12, FloatDelegate(self))
        self.setItemDelegateForColumn(13, FormulaDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragDrop)
        self.table_name = "technosphere"
        self.drag_model = True

    @property
    def df_columns(self) -> list:
        columns = super().df_columns
        start = columns[:columns.index("Formula")]
        end = columns[columns.index("Formula"):]
        return start + ["pedigree"] + self.UNCERTAINTY + end

    def create_row(self, exchange: ExchangeProxyBase) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Product": adj_act.get("reference product") or adj_act.get("name"),
            "Activity": adj_act.get("name"),
            "Location": adj_act.get("location", "Unknown"),
            "Database": adj_act.get("database"),
            "Uncertainty": exchange.get("uncertainty type", 0),
            "Formula": exchange.get("formula"),
        })
        try:
            matrix = PedigreeMatrix.from_dict(exchange.get("pedigree", {}))
            row.update({"pedigree": matrix.factors_as_tuple()})
        except AssertionError:
            row.update({"pedigree": None})
        row.update({
            k: v for k, v in exchange.uncertainty.items() if k in self.UNCERTAINTY
        })
        return row, adj_act

    def _resize(self) -> None:
        """ Ensure the `exchange` column is hidden whenever the table is shown.
        """
        self.setColumnHidden(self.exchange_column, True)
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.df_columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.modify_uncertainty_action)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        """ Accept exchanges from a technosphere database table, and the
        downstream exchanges table.
        """
        source = event.source()
        if (getattr(source, "table_name", "") == "downstream" or
                hasattr(source, "technosphere")):
            event.accept()


class BiosphereExchangeTable(BaseExchangeTable):
    COLUMNS = [
        "Amount", "Unit", "Flow Name", "Compartments", "Database",
        "Uncertainty", "Formula"
    ]
    UNCERTAINTY = [
        "loc", "scale", "shape", "minimum", "maximum"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, FloatDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, UncertaintyDelegate(self))
        self.setItemDelegateForColumn(6, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(7, FloatDelegate(self))
        self.setItemDelegateForColumn(8, FloatDelegate(self))
        self.setItemDelegateForColumn(9, FloatDelegate(self))
        self.setItemDelegateForColumn(10, FloatDelegate(self))
        self.setItemDelegateForColumn(11, FloatDelegate(self))
        self.setItemDelegateForColumn(12, FormulaDelegate(self))
        self.table_name = "biosphere"
        self.setDragDropMode(QtWidgets.QTableView.DropOnly)

    @property
    def df_columns(self) -> list:
        columns = super().df_columns
        start = columns[:columns.index("Formula")]
        end = columns[columns.index("Formula"):]
        return start + ["pedigree"] + self.UNCERTAINTY + end

    def create_row(self, exchange) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Flow Name": adj_act.get("name"),
            "Compartments": " - ".join(adj_act.get('categories', [])),
            "Database": adj_act.get("database"),
            "Uncertainty": exchange.get("uncertainty type", 0),
            "Formula": exchange.get("formula"),
        })
        try:
            matrix = PedigreeMatrix.from_dict(exchange.get("pedigree", {}))
            row.update({"pedigree": matrix.factors_as_tuple()})
        except AssertionError:
            row.update({"pedigree": None})
        row.update({
            k: v for k, v in exchange.uncertainty.items() if k in self.UNCERTAINTY
        })
        return row, adj_act

    def _resize(self) -> None:
        self.setColumnHidden(self.exchange_column, True)
        self.show_uncertainty()

    def show_uncertainty(self, show: bool = False) -> None:
        """Show or hide the uncertainty columns, 'Uncertainty Type' is always shown.
        """
        cols = self.df_columns
        self.setColumnHidden(cols.index("Uncertainty"), not show)
        self.setColumnHidden(cols.index("pedigree"), not show)
        for c in self.UNCERTAINTY:
            self.setColumnHidden(cols.index(c), not show)

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(self.delete_exchange_action)
        menu.addAction(self.remove_formula_action)
        menu.addAction(self.modify_uncertainty_action)
        menu.exec_(a0.globalPos())

    def dragEnterEvent(self, event):
        """ Only accept exchanges from a technosphere database table
        """
        if hasattr(event.source(), "technosphere"):
            event.accept()


class DownstreamExchangeTable(BaseExchangeTable):
    """ Downstream table class is very similar to technosphere table, just more
    restricted.
    """
    COLUMNS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegateForColumn(0, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(1, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(2, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(3, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(4, ViewOnlyDelegate(self))
        self.setItemDelegateForColumn(5, ViewOnlyDelegate(self))
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)

        self.downstream = True
        self.table_name = "downstream"
        self.drag_model = True

    def create_row(self, exchange) -> (dict, object):
        row, adj_act = super().create_row(exchange)
        row.update({
            "Product": adj_act.get("reference product") or adj_act.get("name"),
            "Activity": adj_act.get("name"),
            "Location": adj_act.get("location", "Unknown"),
            "Database": adj_act.get("database"),
        })
        return row, adj_act

    def _resize(self) -> None:
        """ Next to `exchange`, also hide the `formula` column.
        """
        self.setColumnHidden(self.exchange_column, True)

    def contextMenuEvent(self, a0) -> None:
        menu = QtWidgets.QMenu()
        menu.addAction(qicons.right, "Open activities", self.open_activities)
        menu.exec_(a0.globalPos())
