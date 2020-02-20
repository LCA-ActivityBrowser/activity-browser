# -*- coding: utf-8 -*-
from abc import abstractmethod
from collections.abc import Iterator
import itertools
from typing import Iterable, List, Optional, Tuple

from asteval import Interpreter
from bw2data.backends.peewee import ExchangeDataset
from bw2data.parameters import (
    ProjectParameter, DatabaseParameter, ActivityParameter,
    ParameterizedExchange, get_new_symbols
)
from bw2parameters import ParameterSet
from bw2parameters.errors import MissingName
import numpy as np
from stats_arrays import MCRandomNumberGenerator, UncertaintyBase

from .utils import Index, Parameters, Indices, StaticParameters


class ParameterManager(object):
    """A manager for Brightway2 parameters, allowing for formula evaluation
    without touching the database.
    """
    def __init__(self):
        self.parameters: Parameters = Parameters.from_bw_parameters()
        self.initial: StaticParameters = StaticParameters()
        self.indices: Indices = self.construct_indices()

    def construct_indices(self) -> Indices:
        """Given that ParameterizedExchanges will always have the same order of
        indices, construct them once and reuse when needed.
        """
        indices = Indices()
        for p in self.initial.act_by_group_db:
            params = self.initial.exc_by_group(p.group)
            indices.extend(
                Index.build_from_exchange(ExchangeDataset.get_by_id(pk))
                for pk in params
            )
        return indices

    def recalculate_project_parameters(self) -> dict:
        data = self.initial.project()
        if not data:
            return {}

        new_values = self.parameters.data_by_group("project")

        for name, amount in new_values.items():
            data[name]["amount"] = amount

        ParameterSet(data).evaluate_and_set_amount_field()
        return StaticParameters.prune_result_data(data)

    def recalculate_database_parameters(self, database: str, global_params: dict = None) -> dict:
        data = self.initial.by_database(database)
        if not data:
            return {}

        glo = global_params or {}
        new_values = self.parameters.data_by_group(database)
        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(glo)
        if missing:
            raise MissingName("The following variables aren't defined:\n{}".format("|".join(missing)))

        glo = Parameters.static(glo, needed=new_symbols) if new_symbols else None

        ParameterSet(data, glo).evaluate_and_set_amount_field()
        return StaticParameters.prune_result_data(data)

    def process_database_parameters(self, global_params: dict = None) -> dict:
        glo = global_params or self.recalculate_project_parameters()
        all_db = {}
        for database in self.initial.databases:
            db = self.recalculate_database_parameters(database, glo)
            all_db[database] = {x: y for x, y in db.items()} if db else {}
        return all_db

    def recalculate_activity_parameters(self, group: str, global_params: dict = None) -> dict:
        data = self.initial.act_by_group(group)
        if not data:
            return {}

        new_values = self.parameters.data_by_group(group)
        glo = global_params or {}
        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(global_params)
        if missing:
            raise MissingName("The following variables aren't defined:\n{}".format("|".join(missing)))

        glo = Parameters.static(glo, needed=new_symbols) if new_symbols else None

        ParameterSet(data, glo).evaluate_and_set_amount_field()
        return StaticParameters.prune_result_data(data)

    def recalculate_exchanges(self, group: str, global_params: dict = None) -> Iterable[Tuple[int, float]]:
        """ Constructs a list of exc.id/amount tuples for the
        ParameterizedExchanges in the given group.
        """
        params = self.initial.exc_by_group(group)
        if not params:
            return []

        glo = global_params or {}
        interpreter = Interpreter()
        interpreter.symtable.update(glo)
        return [(k, interpreter(v)) for k, v in params.items()]

    def process_exchanges(self, global_params: dict = None, db_params: dict = None,
                          build_indices: bool = True) -> np.ndarray:
        dbs = db_params or {}
        complete_data = np.zeros(len(self.indices))

        offset = 0
        for p in self.initial.act_by_group_db:
            combination = {x: y for x, y in global_params.items()} if global_params else {}
            combination.update(dbs.get(p.database, {}))
            combination.update(self.recalculate_activity_parameters(p.group, combination))

            recalculated = self.recalculate_exchanges(p.group, global_params=combination)
            # If the parameter group contains no ParameterizedExchanges, skip.
            if not recalculated:
                continue
            # `data` contains the recalculated amounts for the exchanges.
            _, data = zip(*recalculated)
            complete_data[offset:len(data) + offset] = data
            offset += len(data)

        return complete_data

    def calculate(self) -> np.ndarray:
        """ Convenience function that takes calculates the current parameters
        and returns a fully-formed set of exchange amounts and indices.

        All parameter types are recalculated in turn before interpreting the
        ParameterizedExchange formulas into amounts.
        """
        global_project = self.recalculate_project_parameters()
        all_db = self.process_database_parameters(global_project)
        data = self.process_exchanges(global_project, all_db)
        return data

    @abstractmethod
    def recalculate(self, values: List[float]) -> np.ndarray:
        """ Convenience function that takes the given new values and recalculates.
        Returning a fully-formed set of exchange amounts and indices.

        All parameter types are recalculated in turn before interpreting the
        ParameterizedExchange formulas into amounts.
        """
        self.parameters.update(values)
        return self.calculate()

    @staticmethod
    def has_parameterized_exchanges() -> bool:
        """ Test if ParameterizedExchanges exist, no point to using this manager
        otherwise.
        """
        return ParameterizedExchange.select().exists()


class MonteCarloParameterManager(ParameterManager, Iterator):
    """Use to sample the uncertainty of parameter values, mostly for use in
    Monte Carlo calculations.

    Each iteration will sample the parameter uncertainty, after which
    all parameters and parameterized exchanges are recalculated. These
    recalculated values are then returned as a simplified `params` array,
    which is similar to the `tech_params` and `bio_params` arrays in the
    LCA classes.

    Makes use of the `MCRandomNumberGenerator` to sample from all of the
    distributions in the same way.

    """

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        parameters = itertools.chain(
            ProjectParameter.select(), DatabaseParameter.select(),
            ActivityParameter.select()
        )
        self.uncertainties = UncertaintyBase.from_dicts(
            *[getattr(p, "data", {}) for p in parameters]
        )
        self.mc_generator = MCRandomNumberGenerator(self.uncertainties, seed=seed)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def recalculate(self, iterations: int = 10) -> np.ndarray:
        assert iterations > 0, "Must have a positive amount of iterations"
        if iterations == 1:
            return self.next()
        # Construct indices, prepare sized array and sample parameter
        # uncertainty distributions `interations` times.
        all_data = np.empty((iterations, len(self.indices)), dtype=Indices.array_dtype)
        random_bounded_values = self.mc_generator.generate(iterations)

        # Now, repeatedly replace parameter amounts with sampled data and
        # recalculate. Every processed row is added to the sized array.
        for i in range(iterations):
            values = random_bounded_values.take(i, axis=1)
            self.parameters.update(values)
            data = self.calculate()
            all_data[i] = self.indices.mock_params(data)

        return all_data

    def next(self) -> np.ndarray:
        """Similar to `recalculate` but only performs a single sampling and
        recalculation.
        """
        values = self.mc_generator.next()
        self.parameters.update(values)
        data = self.calculate()
        return self.indices.mock_params(data)
