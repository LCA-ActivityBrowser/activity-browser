from abc import abstractmethod
from collections.abc import Iterator
from copy import deepcopy
from typing import Iterable, Optional, Tuple

import numpy as np
from stats_arrays import MCRandomNumberGenerator, UncertaintyBase

from bw2data.backends import ExchangeDataset
from bw2data.parameters import get_new_symbols, ParameterizedExchange
from bw2parameters import ParameterSet, MissingName, Interpreter

from .utils import Index, Indices, Parameters, StaticParameters

from loguru import logger

class ParameterManager(object):
    """A manager for Brightway2 parameters, allowing for formula evaluation
    without touching the database.
    """

#TODO: several methods here are only kept as the MonteCarloParameterManager still relies on these
#TODO: once the MonteCarloParameterManager is re-worked, these methods can be removed as well

    def __init__(self):
        self.parameters: Parameters = Parameters.from_bw_parameters()
        self.initial: StaticParameters = StaticParameters()
        self.indices: Indices = self.construct_indices()
        self._active_override_keys: set[tuple[str, str]] = set()

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
        raw = self.initial.project()
        if not raw:
            return {}
        data = deepcopy(raw)

        new_values = self.parameters.data_by_group("project")

        for name, amount in new_values.items():
            data[name]["amount"] = amount
            if ("project", str(name)) in self._active_override_keys:
                data[name]["formula"] = ""

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
            if (str(database), str(name)) in self._active_override_keys:
                data[name]["formula"] = ""

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
            if (str(group), str(name)) in self._active_override_keys:
                data[name]["formula"] = ""

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(global_params)
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
        """Constructs a list of exc.id/amount tuples for the
        ParameterizedExchanges in the given group.
        """
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
        build_indices: bool = True,
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
            # If the parameter group contains no ParameterizedExchanges, skip.
            if not recalculated:
                continue
            # `data` contains the recalculated amounts for the exchanges.
            _, data = zip(*recalculated)
            complete_data[offset : len(data) + offset] = data
            offset += len(data)

        return complete_data

    def calculate(self) -> np.ndarray:
        """Convenience function that takes calculates the current parameters
        and returns a fully-formed set of exchange amounts and indices.

        All parameter types are recalculated in turn before interpreting the
        ParameterizedExchange formulas into amounts.
        """
        global_project = self.recalculate_project_parameters()
        all_db = self.process_database_parameters(global_project)
        data = self.process_exchanges(global_project, all_db)
        return data

    @abstractmethod
    def recalculate(self, values: dict[str, float]) -> np.ndarray:
        """Convenience function that takes the given new values and recalculates.
        Returning a fully-formed set of exchange amounts and indices.

        All parameter types are recalculated in turn before interpreting the
        ParameterizedExchange formulas into amounts.
        """
        self.parameters.update(values)
        return self.calculate()

    @staticmethod
    def _exchange_formula_rows_for_selected_groups(
        selected_groups: set[str],
    ) -> list[tuple[str, int, str, str | None]]:
        """Read formulas directly from exchanges in selected output databases."""
        from bw2data.parameters import ActivityParameter

        # Map output activity keys to activity-parameter groups (if present).
        activity_group_by_key = {}
        for ap in ActivityParameter.select(
            ActivityParameter.group, ActivityParameter.database, ActivityParameter.code
        ).distinct():
            activity_group_by_key[(str(ap.database), str(ap.code))] = str(ap.group)

        rows = []
        try:
            query = ExchangeDataset.select().where(
                ExchangeDataset.output_database << list(selected_groups)
            )
            for exc in query:
                formula = ""
                if isinstance(getattr(exc, "data", None), dict):
                    formula = str((exc.data or {}).get("formula") or "").strip()
                if not formula:
                    formula = str(getattr(exc, "formula", "") or "").strip()
                if formula:
                    activity_group = activity_group_by_key.get(
                        (str(exc.output_database), str(exc.output_code))
                    )
                    rows.append(
                        (
                            str(exc.output_database),
                            int(exc.id),
                            formula,
                            activity_group,
                            0 if str(exc.input_database) == str(exc.output_database) else 1,
                        )
                    )
        except Exception:
            return []
        rows.sort(key=lambda x: (x[0], x[4], x[2], x[1]))
        return [(g, eid, f, act_group) for g, eid, f, act_group, _prio in rows]

    def process_selected_exchange_formulas(
        self,
        project_params: dict,
        database_params: dict,
        selected_groups: set[str],
    ) -> dict[int, float]:
        rows = self._exchange_formula_rows_for_selected_groups(selected_groups)
        if not rows:
            return {}

        complete = {}
        for group, exc_id, formula, activity_group in rows:
            scope = project_params.copy()
            scope.update(database_params.get(group, {}))
            if activity_group:
                activity_params = self.recalculate_activity_parameters(activity_group, scope)
                scope.update(activity_params)
            interpreter = Interpreter()
            interpreter.symtable.update(scope)
            complete[exc_id] = interpreter(formula)
        return complete

    def exchanges_from_scenarios(self, scenario_names, data, selected_groups: set[str] | None = None):
        names = list(scenario_names)
        # Guard against accidental inclusion of a "default" pseudo-scenario name.
        filtered_names = [n for n in names if str(n).strip().lower() != "default"]
        if len(filtered_names) == len(data):
            names = filtered_names
        if len(names) != len(data):
            raise ValueError(
                f"Scenario name/value alignment mismatch: {len(names)} names for {len(data)} value columns"
            )
        scenario_dict = {name: dict(data[i]) for i, name in enumerate(names)}
        scenario_samples = {}
        baseline = {(p.group, p.name): p.amount for p in self.parameters.data}
        selected = set(selected_groups or [])
        if not selected:
            raise ValueError("No selected groups provided for direct exchange conversion")

        for scenario, parameters in scenario_dict.items():
            self._active_override_keys = {
                (str(k[0]), str(k[1]))
                for k, v in parameters.items()
                if isinstance(k, tuple) and len(k) == 2 and not np.isnan(v)
            }
            self.parameters.update(baseline)
            self.parameters.update(parameters)

            project_params = self.recalculate_project_parameters()
            database_params = self.process_database_parameters(project_params)
            direct = self.process_selected_exchange_formulas(
                project_params, database_params, selected
            )
            if not direct:
                raise ValueError(
                    "No direct formula exchanges found for selected groups: "
                    + ", ".join(sorted(selected))
                )
            scenario_samples[scenario] = direct
        self._active_override_keys = set()
        return scenario_samples


class MonteCarloParameterManager(ParameterManager, Iterator):
    # TODO: once the MonteCarloParameterManager is re-worked, remove unnecessary methods from ParameterManager
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
        keys = [(p.group, p.name) for p in self.parameters]
        self.parameters.update({key: value for key, value in zip(keys, values)})
        data = self.calculate()
        return self.indices.mock_params(data)

    def retrieve_sampled_values(self, data: dict):
        """Enters the sampled values into the 'exchanges' list in the 'data'
        dictionary.
        """
        for name, vals in data.items():
            param = next(
                (
                    p
                    for p in self.parameters
                    if p.name == vals.get("name") and p.group == vals.get("group")
                ),
                None,
            )
            if param is None:
                continue
            data[name]["values"].append(param.amount)
