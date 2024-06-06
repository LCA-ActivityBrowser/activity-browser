# -*- coding: utf-8 -*-
import itertools
from typing import Iterable, Optional

import pandas as pd
from asteval import Interpreter
from bw2data.parameters import (ProjectParameter, DatabaseParameter, Group,
                                ActivityParameter)
from bw2data.proxies import ExchangeProxyBase
from peewee import DoesNotExist
from PySide2.QtCore import QModelIndex, Qt, Slot

from activity_browser import log, signals, actions
from activity_browser.bwutils import (
    PedigreeMatrix, commontasks as bc
)
from .base import EditablePandasModel


class BaseExchangeModel(EditablePandasModel):
    COLUMNS = []
    # Fields accepted by brightway to be stored in exchange objects.
    VALID_FIELDS = {
        "amount", "formula", "uncertainty type", "loc", "scale", "shape",
        "minimum", "maximum", "comment"
    }

    def __init__(self, key=None, parent=None):
        super().__init__(parent=parent)
        self.key = key
        self.exchanges = []
        self.exchange_column = 0

    def load(self, exchanges: Iterable):
        self.exchanges = exchanges
        self.sync()

    def sync(self):
        """ Build the table using either new or stored exchanges iterable.
        """
        data = (self.create_row(exc) for exc in self.exchanges)
        self._dataframe = pd.DataFrame([row for row in data if row], columns=self.columns)
        self.exchange_column = self._dataframe.columns.get_loc("exchange")
        self.updated.emit()

    @property
    def columns(self) -> list:
        return self.COLUMNS + ["exchange"]

    def create_row(self, exchange) -> dict:
        """ Take the given Exchange object and extract a number of attributes.
        """
        try:
            row = {
                "Amount": float(exchange.get("amount", 1)),
                "Unit": exchange.input.get("unit", "Unknown"),
                "exchange": exchange,
            }

            # sync when the exchange input or output changes
            exchange.input.changed.connect(self.sync, Qt.UniqueConnection)
            exchange.output.changed.connect(self.sync, Qt.UniqueConnection)

            return row
        except DoesNotExist as e:
            # The input activity does not exist. remove the exchange.
            log.warning(f"Broken exchange: {e}, removing.")
            actions.ExchangeDelete.run([exchange])

    def get_exchange(self, proxy: QModelIndex) -> ExchangeProxyBase:
        idx = self.proxy_to_source(proxy)
        return self._dataframe.iat[idx.row(), self.exchange_column]

    def get_key(self, proxy: QModelIndex) -> tuple:
        """ Get the activity key from an exchange."""
        exchange = self.get_exchange(proxy)
        return exchange.input.key

    def edit_cell(self, proxy: QModelIndex) -> None:
        col = proxy.column()
        if self._dataframe.columns[col] in {'Uncertainty', 'pedigree', 'loc', 'scale',
                                            'shape', 'minimum', 'maximum'}:
            actions.ExchangeUncertaintyModify.run([self.get_exchange(proxy)])

    @Slot(list, name="openActivities")
    def open_activities(self, proxies: list) -> None:
        """ Take the selected indexes and attempt to open activity tabs.
        """
        keys = (self.get_key(p) for p in proxies)
        for key in keys:
            signals.safe_open_activity_tab.emit(key)
            signals.add_activity_to_history.emit(key)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """Whenever data is changed, call an update to the relevant exchange
        or activity.
        """
        header = self._dataframe.columns[index.column()]
        field = bc.AB_names_to_bw_keys.get(header, header)
        exchange = self._dataframe.iat[index.row(), self.exchange_column]
        if field in self.VALID_FIELDS:
            actions.ExchangeModify.run(exchange, {field: value})
        else:
            act_key = exchange.output.key
            actions.ActivityModify.run(act_key, field, value)
        return super().setData(index, value, role)

    def get_usable_parameters(self):
        """ Use the `key` set for the table to determine the database and
        group of the activity, using that information to constrain the usable
        parameters.

        TODO: Move all of the logic to bwutils
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

        TODO: Move logic to bwutils
        """
        interpreter = Interpreter()
        act = ActivityParameter.get_or_none(database=self.key[0], code=self.key[1])
        if act:
            interpreter.symtable.update(ActivityParameter.static(act.group, full=True))
        else:
            log.info("No parameter found for {}, creating one on formula save".format(self.key))
            interpreter.symtable.update(ProjectParameter.static())
            interpreter.symtable.update(DatabaseParameter.static(self.key[0]))
        return interpreter


class ProductExchangeModel(BaseExchangeModel):
    COLUMNS = ["Amount", "Unit", "Product", "Formula"]

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        act = exchange.input
        product = act.get("reference product", act.get("name"))
        row.update({"Product": product, "Formula": exchange.get("formula")})
        return row


class TechnosphereExchangeModel(BaseExchangeModel):
    COLUMNS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database",
        "Uncertainty", "Formula", "Comment"
    ]
    UNCERTAINTY = [
        "loc", "scale", "shape", "minimum", "maximum"
    ]

    @property
    def columns(self) -> list:
        columns = super().columns
        start = columns[:columns.index("Formula")]
        end = columns[columns.index("Formula"):]
        return start + ["pedigree"] + self.UNCERTAINTY + end

    def create_row(self, exchange: ExchangeProxyBase) -> dict:
        row = super().create_row(exchange)
        try:
            act = exchange.input
            row.update({
                "Product": act.get("reference product", act.get("name")),
                "Activity": act.get("name"),
                "Location": act.get("location", "Unknown"),
                "Database": act.get("database"),
                "Uncertainty": exchange.get("uncertainty type", 0),
                "Formula": exchange.get("formula"),
                "Comment": exchange.get("comment"),
            })
            try:
                matrix = PedigreeMatrix.from_dict(exchange.get("pedigree", {}))
                row.update({"pedigree": matrix.factors_as_tuple()})
            except AssertionError:
                row.update({"pedigree": None})
            row.update({
                k: v for k, v in exchange.uncertainty.items() if k in self.UNCERTAINTY
            })
            return row
        except DoesNotExist as e:
            log.info("Exchange was deleted, continue.")
            return {}


class BiosphereExchangeModel(BaseExchangeModel):
    COLUMNS = [
        "Amount", "Unit", "Flow Name", "Compartments", "Database",
        "Uncertainty", "Formula", "Comment"
    ]
    UNCERTAINTY = [
        "loc", "scale", "shape", "minimum", "maximum"
    ]

    @property
    def columns(self) -> list:
        columns = super().columns
        start = columns[:columns.index("Formula")]
        end = columns[columns.index("Formula"):]
        return start + ["pedigree"] + self.UNCERTAINTY + end

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        try:
            act = exchange.input
            row.update({
                "Flow Name": act.get("name"),
                "Compartments": " - ".join(act.get('categories', [])),
                "Database": act.get("database"),
                "Uncertainty": exchange.get("uncertainty type", 0),
                "Formula": exchange.get("formula"),
                "Comment": exchange.get("comment"),
            })
            try:
                matrix = PedigreeMatrix.from_dict(exchange.get("pedigree", {}))
                row.update({"pedigree": matrix.factors_as_tuple()})
            except AssertionError:
                row.update({"pedigree": None})
            row.update({
                k: v for k, v in exchange.uncertainty.items() if k in self.UNCERTAINTY
            })
            return row
        except DoesNotExist as e:
            log.info("Exchange was deleted, continue.")
            return {}


class DownstreamExchangeModel(BaseExchangeModel):
    """ Downstream table class is very similar to technosphere table, just more
    restricted.
    """
    COLUMNS = [
        "Amount", "Unit", "Product", "Activity", "Location", "Database"
    ]

    def create_row(self, exchange) -> dict:
        row = super().create_row(exchange)
        act = exchange.output
        row.update({
            "Product": act.get("reference product", act.get("name")),
            "Activity": act.get("name"),
            "Location": act.get("location", "Unknown"),
            "Database": act.get("database"),
        })
        return row

    def get_key(self, proxy: QModelIndex) -> tuple:
        """ Get the activity key from an exchange."""
        exchange = self.get_exchange(proxy)
        return exchange.output.key
