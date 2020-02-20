# -*- coding: utf-8 -*-
from collections import UserList
from itertools import chain
from typing import Iterable, List, NamedTuple, Optional

from bw2data import config
from bw2data.backends.peewee import ActivityDataset, ExchangeDataset
from bw2data.parameters import (
    ProjectParameter, DatabaseParameter, ActivityParameter,
    ParameterizedExchange,
)
from bw2data.utils import TYPE_DICTIONARY
import numpy as np


"""
This script is a collection of simple NamedTuple classes as well as Iterators
or UserLists specifically built to hold these objects.
 
While not strictly required to run all of the brightway code, these classes do allow
for a significant amount of repeated logic or heavy IO calls to be avoided by either
holding values in memory or allowing simple shortcuts to retrieve them. 
"""


class Parameter(NamedTuple):
    name: str
    group: str
    amount: float = 1.0
    param_type: Optional[str] = None


class Key(NamedTuple):
    database: str
    code: str

    @property
    def database_type(self) -> str:
        return "biosphere" if self.database == config.biosphere else "technosphere"


class Index(NamedTuple):
    input: Key
    output: Key

    @classmethod
    def build_from_exchange(cls, exc: ExchangeDataset) -> 'Index':
        return cls(
            input=Key(exc.input_database, exc.input_code),
            output=Key(exc.output_database, exc.output_code)
        )

    @property
    def input_document_id(self) -> int:
        return ActivityDataset.get(
            ActivityDataset.code == self.input.code,
            ActivityDataset.database == self.input.database
        ).id

    @property
    def output_document_id(self) -> int:
        return ActivityDataset.get(
            ActivityDataset.code == self.output.code,
            ActivityDataset.database == self.output.database
        ).id

    @property
    def exchange_type(self) -> int:
        exc_type = ExchangeDataset.get(
            ExchangeDataset.input_code == self.input.code,
            ExchangeDataset.input_database == self.input.database,
            ExchangeDataset.output_code == self.output.code,
            ExchangeDataset.output_database == self.output.database).type
        return TYPE_DICTIONARY.get(exc_type, -1)

    @property
    def ids_exc_type(self) -> (int, int, int):
        return self.input_document_id, self.output_document_id, self.exchange_type


class Parameters(UserList):
    data: List[Parameter]

    @classmethod
    def from_bw_parameters(cls) -> 'Parameters':
        """Construct a Parameters list from brightway2 parameters."""
        return cls(chain(
            (Parameter(p.name, "project", p.amount, "project")
             for p in ProjectParameter.select()),
            (Parameter(p.name, p.database, p.amount, "database")
             for p in DatabaseParameter.select()),
            (Parameter(p.name, p.group, p.amount, "activity")
             for p in ActivityParameter.select()),
        ))

    def by_group(self, group: str) -> Iterable[Parameter]:
        return (p for p in self.data if p.group == group)

    def data_by_group(self, group: str) -> dict:
        """Parses the `data` to extract the relevant subset of parameters."""
        return {p.name: p.amount for p in self.data if p.group == group}

    @staticmethod
    def static(data: dict, needed: set) -> dict:
        """Similar to the `static` method for each Parameter class where the
        ``needed`` variable is a set of the keys actually needed from ``data``.
        """
        return {k: data[k] for k in data.keys() & needed}

    def update(self, values: Iterable[float]) -> None:
        """Replace parameters in the list if their linked value is not
        NaN.
        """
        assert len(values) == len(self.data)
        for i, (p, v) in enumerate(zip(self.data, values)):
            if not np.isnan(v):
                self.data[i] = p._replace(amount=v)


class Indices(UserList):
    data: List[Index]

    array_dtype = [
        ('input', '<u4'), ('output', '<u4'), ('type', 'u1'), ('amount', '<f4')
    ]

    def mock_params(self, values) -> np.ndarray:
        """Using the given values, construct a numpy array that can be used
        to match against the `tech_params` and `bio_params` arrays of the
        brightway LCA classes.
        """
        assert len(self.data) == len(values)
        data = np.zeros(len(self.data), dtype=self.array_dtype)
        for i, d in enumerate(self.data):
            data[i] = (*d.ids_exc_type, values[i])
        return data


class StaticParameters(object):
    """Contains the initial values for all the parameters in the project.

    This object should be initialized once, after which the methods can be
    used to read out parameter information as it was stored in the database
    originally. This avoids a lot of database calls in repeated recalculations.
    """

    def __init__(self):
        self._project_params = ProjectParameter.load()
        self._db_params = {
            p.database: DatabaseParameter.load(p.database)
            for p in DatabaseParameter.select(DatabaseParameter.database).distinct()
        }
        self._act_params = {
            p.group: ActivityParameter.load(p.group)
            for p in ActivityParameter.select(ActivityParameter.group).distinct()
        }
        self._distinct_act_params = [
            p for p in (ActivityParameter
                        .select(ActivityParameter.group, ActivityParameter.database)
                        .distinct())
        ]
        self._exc_params = [p for p in ParameterizedExchange.select()]

    def project(self) -> dict:
        """Mirrors `ProjectParameter.load()`."""
        return {k: v for k, v in self._project_params.items()}

    @property
    def databases(self) -> set:
        return set(self._db_params)

    def by_database(self, database: str) -> dict:
        """Mirrors `DatabaseParameter.load(database)`."""
        return {k: v for k, v in self._db_params.get(database, {}).items()}

    @property
    def groups(self) -> set:
        groups = set(self._act_params)
        return groups.union(p.group for p in self._exc_params)

    def act_by_group(self, group: str) -> dict:
        """Mirrors `ActivityParameter.load(group)`"""
        return {k: v for k, v in self._act_params.get(group, {}).items()}

    @property
    def act_by_group_db(self) -> list:
        return self._distinct_act_params

    def exc_by_group(self, group: str) -> dict:
        """Mirrors `ParameterizedExchange.load(group)`"""
        return {
            p.exchange: p.formula for p in self._exc_params if p.group == group
        }

    @staticmethod
    def prune_result_data(data: dict) -> dict:
        return {k: v.get("amount") for k, v in data.items()}
