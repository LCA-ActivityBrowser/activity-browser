from abc import abstractmethod
from collections import defaultdict
from collections.abc import Iterator
from typing import Iterable, Optional, Tuple

import numpy as np
from stats_arrays import MCRandomNumberGenerator, UncertaintyBase

from bw2data.backends import ExchangeDataset
from bw2data.parameters import get_new_symbols, ParameterizedExchange
from bw2calc import LCA
from bw2parameters import ParameterSet, MissingName, Interpreter

from .utils import Index, Indices, Parameters, StaticParameters


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

    def recalculate_database_parameters(
        self, database: str, global_params: dict = None
    ) -> dict:
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

    def ps_recalculate(self, values: dict[str, float]) -> np.ndarray:
        """Used to recalculate brightway parameters without editing the database.
        Leftover from Presamples.

        Side-note on presamples: Presamples was used in AB for calculating scenarios,
        presamples was superseded by this implementation. For more reading:
        https://presamples.readthedocs.io/en/latest/index.html"""
        data = self.recalculate(values)
        # After recalculating all the exchanges format them according to
        # presamples requirements: samples as a column of floats.
        samples = data.reshape(1, -1).T
        return samples

    def reformat_indices(self) -> np.ndarray:
        """Additional information is required for storing the indices as presamples.
        Leftover from Presamples.

        Side-note on presamples: Presamples was used in AB for calculating scenarios,
        presamples was superseded by this implementation. For more reading:
        https://presamples.readthedocs.io/en/latest/index.html"""
        result = np.zeros(len(self.indices), dtype=object)
        for i, idx in enumerate(self.indices):
            result[i] = (idx.input, idx.output, idx.flow_type)
        return result

    def arrays_from_scenarios(self, scenarios) -> (np.ndarray, np.ndarray):
        """Used to generate exchange scenario data from parameter scenario data.
        Leftover from Presamples.

        Side-note on presamples: Presamples was used in AB for calculating scenarios,
        presamples was superseded by this implementation. For more reading:
        https://presamples.readthedocs.io/en/latest/index.html"""
        sample_data = [self.ps_recalculate(values.to_dict()) for _, values in scenarios]
        samples = np.concatenate(sample_data, axis=1)
        indices = self.reformat_indices()
        return samples, indices

    @staticmethod
    def has_parameterized_exchanges() -> bool:
        """Test if ParameterizedExchanges exist, no point to using this manager
        otherwise.
        """
        return ParameterizedExchange.select().exists()

    def parameter_exchange_dependencies(self) -> dict:
        """

        Schema: {param1: List[tuple], param2: List[tuple]}
        """
        parameters = defaultdict(list)
        for act in self.initial.act_by_group_db:
            exchanges = self.initial.exc_by_group(act.group)
            for exc, formula in exchanges.items():
                params = get_new_symbols([formula])
                # Convert exchange from int to Index
                exc = Index.build_from_exchange(ExchangeDataset.get_by_id(exc))
                for param in params:
                    parameters[param].append(exc)
        return parameters

    def extract_active_parameters(self, lca: LCA) -> dict:
        """Given an LCA object, extract the used exchanges and build a
        dictionary of parameters with the exchanges that use these parameters.

        Schema: {param1: {"name":  str, "act": Optional[tuple],
                          "group": str, "exchanges": List[tuple]}}
        """
        params = self.parameter_exchange_dependencies()
        used_exchanges = set(lca.biosphere_dict.keys())
        used_exchanges = used_exchanges.union(lca.activity_dict.keys())

        # Make a pass through the 'params' dictionary and remove exchanges
        # that don't exist in the 'used_exchanges' set.
        for p in params:
            keep = [
                i
                for i, exc in enumerate(params[p])
                if (exc.input in used_exchanges and exc.output in used_exchanges)
            ]
            params[p] = [params[p][i] for i in keep]
        # Now only keep parameters with exchanges.
        keep = [p for p, excs in params.items() if len(excs) > 0]
        schema = {
            p: {"name": p, "act": None, "group": None, "exchanges": params[p]}
            for p in keep
        }
        # Now start filling in the parameters that remain with information.
        for group in self.initial.groups:
            for name, data in self.initial.act_by_group(group).items():
                key = (data.get("database"), data.get("code"))
                if name in schema:
                    # Make sure that the activity parameter matches the
                    # output of the exchange.
                    exc = next(e.output for e in schema[name]["exchanges"])
                    if key == exc:
                        schema[name]["name"] = name
                        schema[name]["group"] = group
                        schema[name]["act"] = key
        # Lastly, determine for the remaining parameters if they are database
        # or project parameters.
        for db in self.initial.databases:
            for name, data in self.initial.by_database(db).items():
                if name in schema and schema[name]["group"] is None:
                    schema[name]["group"] = db
        for name in (n for n in schema if schema[n]["group"] is None):
            schema[name]["group"] = "project"
        return schema

    def new_process_exchanges(self, project_params: dict, database_params: dict):
        complete = {}
        for p in self.initial.act_by_group_db:

            scope = project_params.copy()
            scope.update(database_params.get(p.database, {}))

            activity_params = self.recalculate_activity_parameters(p.group, scope)

            scope.update(activity_params)

            exchanges = {exc_id: value for exc_id, value in self.recalculate_exchanges(p.group, scope)}

            complete.update(exchanges)

        return complete

    def exchanges_from_scenarios(self, scenario_names, data):
        scenario_dict = {name: dict(data[i]) for i, name in enumerate(scenario_names)}
        scenario_samples = {}

        for scenario, parameters in scenario_dict.items():
            self.parameters.update(parameters)

            project_params = self.recalculate_project_parameters()
            database_params = self.process_database_parameters(project_params)
            scenario_samples[scenario] = self.new_process_exchanges(project_params, database_params)
        return scenario_samples


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
