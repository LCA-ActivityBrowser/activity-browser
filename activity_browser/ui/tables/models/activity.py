# -*- coding: utf-8 -*-
import itertools
from typing import Any, Iterable, Optional
from logging import getLogger

import pandas as pd
from asteval import Interpreter
from peewee import DoesNotExist

from qtpy import QtCore
from qtpy.QtCore import QModelIndex, Qt, Slot

from bw2data.parameters import ActivityParameter, DatabaseParameter, Group, ProjectParameter
from bw2data.proxies import ExchangeProxyBase
from bw2data.errors import UnknownObject

from activity_browser import actions, signals
from activity_browser.actions.activity.activity_redo_allocation import MultifunctionalProcessRedoAllocation
from activity_browser.bwutils import PedigreeMatrix
from activity_browser.bwutils import commontasks as bc

from .base import EditablePandasModel

log = getLogger(__name__)


class BaseExchangeModel(EditablePandasModel):
    COLUMNS = []
    # Fields accepted by brightway to be stored in exchange objects.
    VALID_FIELDS = {
        "amount",
        "formula",
        "uncertainty type",
        "loc",
        "scale",
        "shape",
        "minimum",
        "maximum",
        "comment",
        "functional",
    }
    UNCERTAINTY_ITEMS = ["loc", "scale", "shape", "minimum", "maximum"]

    def __init__(self, key=None, parent=None):
        super().__init__(parent=parent)
        self.key = key
        self.exchanges = []
        self.exchange_column = 0
        # Query column names
        self._columns = list(self.create_row(None).keys())

    def load(self, exchanges: Iterable):
        self.exchanges = exchanges
        self.sync()

    def sync(self):
        """Build the table using either new or stored exchanges iterable."""
        data = (self.create_row(exc) for exc in self.exchanges if exc.valid())
        self._dataframe = pd.DataFrame(
            [row for row in data if row], columns=self.columns
        )
        self.exchange_column = self._dataframe.columns.get_loc("exchange")
        self.updated.emit()

    @property
    def columns(self) -> list[str]:
        # return self.COLUMNS + ["exchange"]
        return self._columns

    def create_row(self, exchange: Optional[ExchangeProxyBase]) -> dict[str, Any]:
        """Take the given Exchange object and extract a number of attributes."""
        try:
            row = {}
            self.update_row_with_common_columns(row, exchange)
            return row
        except UnknownObject as e:
            # The input activity does not exist. remove the exchange.
            log.warning(f"Broken exchange: {exchange}, removing.")
            actions.ExchangeDelete.run([exchange])

    @staticmethod
    def update_row_with_common_columns(row: dict[str, Any],
                                       exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                exchange.input.get("name")
                exchange.output.get("name")
            except UnknownObject:
                # broken exchange
                row.update({"Amount": float(exchange.get("amount", 1))})
                return
            row.update({
                "Amount": float(exchange.get("amount", 1)),
                "Unit": exchange.input.get("unit", "Unknown"),
                "exchange": exchange,
            })
        else:
            row.update({
                "Amount": "",
                "Unit": "",
                "exchange": None,
            })

    @staticmethod
    def update_row_with_node_name(row: dict[str, Any], col_name: str,
                                  exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            act = exchange.input
            row.update({
                col_name: act.get("name"),
            })
        else:
            row.update({
                col_name: "",
            })

    @staticmethod
    def update_row_with_product_name(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        from bw_functional import Function

        if exchange is not None:
            try:
                act = exchange.input
                product = act.get("name") if isinstance(act, Function) else act.get("reference product", act.get("name"))
                row.update({
                    "Product": product,
                })
            except UnknownObject:
                row.update({
                    "Product": "EXCHANGE NOT FOUND",
                })
        else:
            row.update({
                "Product": "",
            })

    @staticmethod
    def update_row_with_functional(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                row.update({
                    "Functional": str(exchange.get("functional", False)),
                    "Allocation factor": as_number(exchange.input.get('allocation_factor')),
                })
            except UnknownObject:
                pass
        else:
            row.update({
                "Functional": "",
                "Allocation factor": "",
            })

    @staticmethod
    def update_row_with_categories(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                act = exchange.input
                row.update({
                    "Compartments": " - ".join(act.get("categories", [])),
                })
            except UnknownObject:
                pass
        else:
            row.update({
                "Compartments": "",
            })

    @staticmethod
    def update_row_with_location(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                act = exchange.input
                row.update({
                    "Location": act.get("location", "Unknown"),
                })
            except UnknownObject:
                pass
        else:
            row.update({
                "Location": "",
            })

    @staticmethod
    def update_row_with_database(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                act = exchange.input
                row.update({
                    "Database": act.get("database"),
                })
            except UnknownObject:
                pass
        else:
            row.update({
                "Database": "",
            })

    @staticmethod
    def update_row_with_uncertainty_type(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            row.update({
                "Uncertainty": exchange.get("uncertainty type", 0),
            })
        else:
            row.update({
                "Uncertainty": "",
            })

    @staticmethod
    def update_row_with_pedigree(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            try:
                matrix = PedigreeMatrix.from_dict(exchange.get("pedigree", {}))
                row.update({"pedigree": matrix.factors_as_tuple()})
            except AssertionError:
                row.update({"pedigree": None})
        else:
            row.update({"pedigree": ""})

    @staticmethod
    def update_row_with_uncertainty_items(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            row.update(
                {k: v for k, v in exchange.uncertainty.items() if k in BaseExchangeModel.UNCERTAINTY_ITEMS}
            )
        else:
            row.update(
                {k: "" for k in BaseExchangeModel.UNCERTAINTY_ITEMS}
            )

    @staticmethod
    def update_row_with_formula(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            row.update({
                "Formula": exchange.get("formula"),
            })
        else:
            row.update({
                "Formula": "",
            })

    @staticmethod
    def update_row_with_comment(row: dict[str, Any], exchange: Optional[ExchangeProxyBase]):
        if exchange is not None:
            row.update({
                "Comment": exchange.get("comment"),
            })
        else:
            row.update({
                "Comment": "",
            })

    def get_exchange(self, proxy: QModelIndex) -> ExchangeProxyBase:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.exchange_column]

    def get_key(self, proxy: QModelIndex) -> tuple:
        """Get the activity key from an exchange."""
        exchange = self.get_exchange(proxy)
        return exchange.input.key

    def edit_cell(self, proxy: QModelIndex) -> None:
        col = proxy.column()
        if self._dataframe.columns[col] in {
            "Uncertainty",
            "pedigree",
            "loc",
            "scale",
            "shape",
            "minimum",
            "maximum",
            "functional",
        }:
            actions.ExchangeUncertaintyModify.run([self.get_exchange(proxy)])

    @Slot(list, name="openActivities")
    def open_activities(self, proxies: list) -> None:
        """Take the selected indexes and attempt to open activity tabs."""
        keys = (self.get_key(p) for p in proxies)
        for key in keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Whenever data is changed, call an update to the relevant exchange
        or activity.
        """
        from bw_functional import Function

        if index.isValid() and not self._read_only:
            value, check_ok = self.prepare_set_value(index, value, role)
            if role == Qt.EditRole or check_ok:
                header = self._dataframe.columns[index.column()]
                field = bc.AB_names_to_bw_keys.get(header, header)
                exchange = self._dataframe.iat[index.row(), self.exchange_column]
                if field in self.VALID_FIELDS:
                    actions.ExchangeModify.run(exchange, {field: value})
                elif header == "Product" and isinstance(exchange.input, Function):
                    actions.ActivityModify.run(exchange.input.key, "name", value)
                else:
                    act_key = exchange.input.key
                    actions.ActivityModify.run(act_key, field, value)
                # This is actually, not entirely correct. The data in the table
                # has not been changed yet, it will be when the updates from
                # above changes trigger. But the underlying data has been changed.
                self.dataChanged.emit(index, index, [role])

        return False

    def get_usable_parameters(self):
        """Use the `key` set for the table to determine the database and
        group of the activity, using that information to constrain the usable
        parameters.

        TODO: Move all of the logic to bwutils
        """
        project = ([k, v, "project"] for k, v in ProjectParameter.static().items())
        if self.key is None:
            return project

        database = (
            [k, v, "database"] for k, v in DatabaseParameter.static(self.key[0]).items()
        )

        # Determine if the activity is already part of a parameter group.
        query = (
            Group.select()
            .join(ActivityParameter, on=(Group.name == ActivityParameter.group))
            .where(
                ActivityParameter.database == self.key[0],
                ActivityParameter.code == self.key[1],
            )
            .distinct()
        )
        if query.exists():
            group = query.get()
            # First, build a list for parameters in the same group
            activity = (
                [p.name, p.amount, "activity"]
                for p in ActivityParameter.select().where(
                    ActivityParameter.group == group.name
                )
            )
            # Then extend the list with parameters from groups in the `order`
            # field
            additions = (
                [p.name, p.amount, "activity"]
                for p in ActivityParameter.select().where(
                    ActivityParameter.group << group.order
                )
            )
            activity = itertools.chain(activity, additions)
        else:
            activity = []

        return itertools.chain(project, database, activity)

    def get_interpreter(self) -> Interpreter:
        """Use the activity key to determine which symbols are added
        to the formula interpreter.

        TODO: Move logic to bwutils
        """
        interpreter = Interpreter()
        act = ActivityParameter.get_or_none(database=self.key[0], code=self.key[1])
        if act:
            interpreter.symtable.update(ActivityParameter.static(act.group, full=True))
        else:
            log.info(
                "No parameter found for {}, creating one on formula save".format(
                    self.key
                )
            )
            interpreter.symtable.update(ProjectParameter.static())
            interpreter.symtable.update(DatabaseParameter.static(self.key[0]))
        return interpreter


def as_number(o) -> str:
    if o is None:
        return "(unknown)"
    return "{:.2f}".format(o)


class ProductExchangeModel(BaseExchangeModel):

    def __init__(self, key=None, parent=None):
        super().__init__(key, parent)
        self.set_readonly_column(self.columns.index("Allocation factor"))
        #self.set_builtin_checkbox_delegate(self.columns.index("Functional"), show_text_value = False)

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        self.update_row_with_product_name(row, exchange)
        self.update_row_with_functional(row, exchange)
        self.update_row_with_location(row, exchange) # new
        self.update_row_with_database(row, exchange) # new
        self.update_row_with_uncertainty_type(row, exchange) # new
        self.update_row_with_pedigree(row, exchange) # new
        self.update_row_with_uncertainty_items(row, exchange) # new
        self.update_row_with_formula(row, exchange)
        self.update_row_with_comment(row, exchange) # new
        return row


class TechnosphereExchangeModel(BaseExchangeModel):

    def __init__(self, key=None, parent=None):
        super().__init__(key, parent)
        self.set_readonly_column(self.columns.index("Allocation factor"))
        # self.set_builtin_checkbox_delegate(self.columns.index("Functional"), show_text_value = False)

    def create_row(self, exchange: ExchangeProxyBase) -> dict:
        row = super().create_row(exchange)
        self.update_row_with_product_name(row, exchange)
        self.update_row_with_functional(row, exchange)
        self.update_row_with_node_name(row, "Activity", exchange) # diff from first
        self.update_row_with_location(row, exchange)
        self.update_row_with_database(row, exchange)
        self.update_row_with_uncertainty_type(row, exchange)
        self.update_row_with_pedigree(row, exchange)
        self.update_row_with_uncertainty_items(row, exchange)
        self.update_row_with_formula(row, exchange)
        self.update_row_with_comment(row, exchange)
        return row


class BiosphereExchangeModel(BaseExchangeModel):

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        self.update_row_with_node_name(row, "Flow Name", exchange)
        self.update_row_with_categories(row, exchange)
        self.update_row_with_location(row, exchange) # new
        self.update_row_with_database(row, exchange)
        self.update_row_with_uncertainty_type(row, exchange)
        self.update_row_with_pedigree(row, exchange)
        self.update_row_with_uncertainty_items(row, exchange) # new
        self.update_row_with_formula(row, exchange)
        self.update_row_with_comment(row, exchange)

        return row


class DownstreamExchangeModel(BaseExchangeModel):
    """Downstream table class is very similar to technosphere table, just more
    restricted.
    """

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        self.update_row_with_product_name(row, exchange)
        self.update_row_with_node_name(row, "Activity", exchange) # diff from first
        self.update_row_with_location(row, exchange)
        self.update_row_with_database(row, exchange)
        return row

    def get_key(self, proxy: QModelIndex) -> tuple:
        """Get the activity key from an exchange."""
        exchange = self.get_exchange(proxy)
        return exchange.output.key
