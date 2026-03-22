from collections import UserList
from itertools import chain
from typing import Iterable, List, NamedTuple, Optional

import numpy as np
import peewee as pw
from stats_arrays import UncertaintyBase

import bw2data as bd
from bw2data.backends import ActivityDataset, ExchangeDataset
from bw2data.parameters import ActivityParameter, DatabaseParameter, ParameterizedExchange, ProjectParameter

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
    data: dict = {}
    param_type: Optional[str] = None

    @property
    def deletable(self):
        try:
            return self.to_peewee_model().is_deletable()
        except pw.DoesNotExist:
            return False

    def as_gsa_tuple(self) -> tuple:
        """Return the parameter data formatted as follows:
        - Parameter name
        - Scope [global/activity]
        - Associated activity [or None]
        - Value
        """
        if self.group == "project" or self.group in bd.databases:
            scope = "global"
            associated = None
        else:
            scope = "activity"
            p = ActivityParameter.get(name=self.name, group=self.group)
            associated = (p.database, p.code)
        return self.name, scope, associated, self.amount

    def to_peewee_model(self):
        if not self.param_type:
            raise ValueError("Cannot refresh parameter without parameter type")
        if self.param_type == "project":
            return ProjectParameter.get(ProjectParameter.name == self.name)
        elif self.param_type == "database":
            return DatabaseParameter.get((DatabaseParameter.name == self.name) & (DatabaseParameter.database == self.group))
        elif self.param_type == "activity":
            return ActivityParameter.get((ActivityParameter.name == self.name) & (ActivityParameter.group == self.group))
        else:
            raise ValueError("Unknown parameter type")


class Key(NamedTuple):
    database: str
    code: str

    @property
    def database_type(self) -> str:
        return "biosphere" if self.database == bd.config.biosphere else "technosphere"


class Index(NamedTuple):
    input: Key
    output: Key
    flow_type: Optional[str] = None
    input_id: Optional[int] = None
    output_id: Optional[int] = None

    @classmethod
    def build_from_exchange(cls, exc: ExchangeDataset) -> "Index":
        return cls(
            input=Key(exc.input_database, exc.input_code),
            output=Key(exc.output_database, exc.output_code),
            flow_type=exc.type,
        )

    @classmethod
    def build_from_tuple(cls, data: tuple) -> "Index":
        obj = cls(
            input=Key(data[0][0], data[0][1]),
            output=Key(data[1][0], data[1][1]),
        )
        exc_type = ExchangeDataset.get(
            ExchangeDataset.input_code == obj.input.code,
            ExchangeDataset.input_database == obj.input.database,
            ExchangeDataset.output_code == obj.output.code,
            ExchangeDataset.output_database == obj.output.database,
        ).type
        return obj._replace(flow_type=exc_type)

    @classmethod
    def build_from_dict(cls, data: dict) -> "Index":
        in_key = data.get("input", ("", ""))
        out_key = data.get("output", ("", ""))

        input_id = data.get("input_id", None)
        output_id = data.get("output_id", None)

        return cls(
            input=Key(in_key[0], in_key[1]),
            output=Key(out_key[0], out_key[1]),
            flow_type=data.get("flow type", None),
            input_id=input_id,
            output_id=output_id,
        )

    @property
    def input_document_id(self) -> int:
        return ActivityDataset.get(
            ActivityDataset.code == self.input.code,
            ActivityDataset.database == self.input.database,
        ).id

    @property
    def output_document_id(self) -> int:
        return ActivityDataset.get(
            ActivityDataset.code == self.output.code,
            ActivityDataset.database == self.output.database,
        ).id

    @property
    def exchange_type(self) -> int:
        raise NotImplementedError("Not available in Brightway25")

    @property
    def flip(self) -> bool:
        if not self.flow_type:
            self.flow_type = ExchangeDataset.get(
                ExchangeDataset.input_code == self.input.code,
                ExchangeDataset.input_database == self.input.database,
                ExchangeDataset.output_code == self.output.code,
                ExchangeDataset.output_database == self.output.database,
            ).type
        return self.flow_type in bd.configuration.labels.technosphere_negative_edge_types


class Parameters(UserList):
    data: List[Parameter]

    @classmethod
    def from_bw_parameters(cls) -> "Parameters":
        """Construct a Parameters list from brightway2 parameters."""
        return cls(
            chain(
                (
                    Parameter(p.name, "project", p.amount, p.data, "project")
                    for p in ProjectParameter.select()
                ),
                (
                    Parameter(p.name, p.database, p.amount, p.data, "database")
                    for p in DatabaseParameter.select()
                ),
                (
                    Parameter(p.name, p.group, p.amount, p.data, "activity")
                    for p in ActivityParameter.select()
                ),
            )
        )

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

    def update(self, new_values: dict[tuple[str, str], float]) -> None:
        """Replace parameters in the list if their linked value is not
        NaN.
        """
        param_by_name = {(p.group, p.name): p for p in self.data}
        index_by_name = {(p.group, p.name): i for i, p in enumerate(self.data)}

        for name, value in new_values.items():
            if not np.isnan(value):
                self.data[index_by_name[name]] = param_by_name[name]._replace(amount=value)
        return
        # for i, (p, v) in enumerate(zip(self.data, values)):
        #     if not np.isnan(v):
        #         self.data[i] = p._replace(amount=v)

    def to_gsa(self) -> List[tuple]:
        """Formats all of the parameters in the list for handling in a GSA."""
        return [p.as_gsa_tuple() for p in self.data]


class Indices(UserList):
    data: List[Index]

    array_dtype = [("input", "O"), ("output", "O"), ("type", "u1"), ("amount", "<f4")]

    def mock_params(self, values) -> np.ndarray:
        """Using the given values, construct a numpy array that can be used
        to match against the `tech_params` and `bio_params` arrays of the
        brightway LCA classes.
        """
        assert len(self.data) == len(values)
        data = np.zeros(len(self.data), dtype=self.array_dtype)
        for i, d in enumerate(self.data):
            data[i] = (d.input, d.output, d.exchange_type, values[i])
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
            p
            for p in (
                ActivityParameter.select(
                    ActivityParameter.group, ActivityParameter.database
                ).distinct()
            )
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
        return {p.exchange: p.formula for p in self._exc_params if p.group == group}

    @staticmethod
    def prune_result_data(data: dict) -> dict:
        return {k: v.get("amount") for k, v in data.items()}
