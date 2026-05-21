"""In-memory parameter recalculation (project → database → activity → exchanges)."""

from abc import abstractmethod
from collections.abc import Iterator
from copy import deepcopy
from typing import Iterable, Optional, Tuple

import numpy as np
from stats_arrays import MCRandomNumberGenerator, UncertaintyBase

from bw2data.backends import ExchangeDataset
from bw2data.parameters import get_new_symbols, ParameterizedExchange
from bw2parameters import Interpreter, MissingName, ParameterSet

from activity_browser.bwutils.utils import Index, Indices, Parameters, StaticParameters


class ParameterManager:
    """
    Evaluate Brightway parameter formulas without writing to the database.

    Recalculation order: project → database → activity parameters, then
    parameterized exchange formulas (per activity group).
    """

    def __init__(self):
        self.parameters: Parameters = Parameters.from_bw_parameters()
        self.initial: StaticParameters = StaticParameters()
        self.indices: Indices = self.construct_indices()

    def construct_indices(self) -> Indices:
        """Build stable exchange indices for all parameterized exchanges in the project."""
        indices = Indices()
        for p in self.initial.act_by_group_db:
            params = self.initial.exc_by_group(p.group)
            indices.extend(
                Index.build_from_exchange(ExchangeDataset.get_by_id(pk))
                for pk in params
            )
        return indices

    def recalculate_project_parameters(self) -> dict:
        raw = self.initial.project()
        if not raw:
            return {}
        data = deepcopy(raw)

        new_values = self.parameters.data_by_group("project")
        for name, amount in new_values.items():
            data[name]["amount"] = amount

        ParameterSet(data).evaluate_and_set_amount_field()
        return StaticParameters.prune_result_data(data)

    def recalculate_database_parameters(
        self, database: str, global_params: dict = None
    ) -> dict:
        raw = self.initial.by_database(database)
        if not raw:
            return {}
        data = deepcopy(raw)

        glo = global_params or {}
        new_values = self.parameters.data_by_group(database)
        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(glo)
        if missing:
            raise MissingName(
                "The following variables aren't defined:\n{}".format("|".join(missing))
            )

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

    def recalculate_activity_parameters(
        self, group: str, global_params: dict = None
    ) -> dict:
        raw = self.initial.act_by_group(group)
        if not raw:
            return {}
        data = deepcopy(raw)

        new_values = self.parameters.data_by_group(group)
        glo = global_params or {}
        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(glo)
        if missing:
            raise MissingName(
                "The following variables aren't defined:\n{}".format("|".join(missing))
            )

        glo = Parameters.static(glo, needed=new_symbols) if new_symbols else None
        ParameterSet(data, glo).evaluate_and_set_amount_field()
        return StaticParameters.prune_result_data(data)

    def recalculate_exchanges(
        self, group: str, global_params: dict = None
    ) -> Iterable[Tuple[int, float]]:
        """Return ``(exchange_id, amount)`` for parameterized exchanges in a group."""
        params = self.initial.exc_by_group(group)
        if not params:
            return []

        glo = global_params or {}
        interpreter = Interpreter()
        interpreter.symtable.update(glo)
        return [(k, interpreter(v)) for k, v in params.items()]

    def process_exchanges(
        self,
        global_params: dict = None,
        db_params: dict = None,
    ) -> np.ndarray:
        dbs = db_params or {}
        complete_data = np.zeros(len(self.indices))

        offset = 0
        for p in self.initial.act_by_group_db:
            combination = (
                {x: y for x, y in global_params.items()} if global_params else {}
            )
            combination.update(dbs.get(p.database, {}))
            combination.update(
                self.recalculate_activity_parameters(p.group, combination)
            )

            recalculated = self.recalculate_exchanges(
                p.group, global_params=combination
            )
            if not recalculated:
                continue
            _, data = zip(*recalculated)
            complete_data[offset : len(data) + offset] = data
            offset += len(data)

        return complete_data

    def calculate(self) -> np.ndarray:
        """Recalculate all parameters and return exchange amounts (index order)."""
        global_project = self.recalculate_project_parameters()
        all_db = self.process_database_parameters(global_project)
        return self.process_exchanges(global_project, all_db)

    @abstractmethod
    def recalculate(self, values: dict[str, float]) -> np.ndarray:
        self.parameters.update(values)
        return self.calculate()


class MonteCarloParameterManager(ParameterManager, Iterator):
    """
    Sample uncertain parameters and recalculate exchange amounts each draw.

    Output rows match ``Indices.mock_params`` for
    :func:`~activity_browser.bwutils.parameters.parameter_montecarlo.apply_parameter_exchanges`.
    """

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
        self.uncertainties = UncertaintyBase.from_dicts(
            *[p.data for p in self.parameters]
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
        all_data = np.empty((iterations, len(self.indices)), dtype=Indices.array_dtype)
        random_bounded_values = self.mc_generator.generate(iterations)

        for i in range(iterations):
            values = random_bounded_values.take(i, axis=1)
            self.parameters.update(values)
            data = self.calculate()
            all_data[i] = self.indices.mock_params(data)

        return all_data

    def next(self) -> np.ndarray:
        values = self.mc_generator.next()
        keys = [(p.group, p.name) for p in self.parameters]
        self.parameters.update({key: value for key, value in zip(keys, values)})
        data = self.calculate()
        return self.indices.mock_params(data)
