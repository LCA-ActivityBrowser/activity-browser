# -*- coding: utf-8 -*-
import itertools
from typing import Iterable, List, Optional, Tuple

from asteval import Interpreter
import brightway2 as bw
from bw2data.backends.peewee import ExchangeDataset
from bw2data.parameters import (ActivityParameter, DatabaseParameter,
                                ParameterizedExchange, ProjectParameter,
                                get_new_symbols)
from bw2parameters import ParameterSet
from bw2parameters.errors import MissingName
import numpy as np
import presamples as ps


class PresamplesParameterManager(object):
    """ Used to recalculate brightway parameters without editing the database

    The `param_values` property and `get_altered_values` method are used to
    retrieve either the whole list of prepared parameter values or a
    subset of it selected by group.

    The `recalculate_*` methods are used to perform the actual calculations
    and will read out the relevant parameters from the database. Each of the
    methods will optionally return a dictionary of the parameter names
    with their recalculated amounts.

    """
    __slots__ = 'parameter_values'

    def __init__(self):
        self.parameter_values: List[tuple] = []

    @property
    def param_values(self) -> Iterable[tuple]:
        return self.parameter_values

    @param_values.setter
    def param_values(self, values: Iterable[tuple]) -> None:
        if isinstance(values, list):
            self.parameter_values = values
        else:
            self.parameter_values = list(values)

    def get_altered_values(self, group: str) -> dict:
        """ Parses the `param_values` to extract the relevant subset of
        changed parameters.
        """
        return {k: v for k, g, v in self.param_values if g == group}

    @classmethod
    def construct(cls, scenario_values: Iterable[float] = None) -> 'PresamplesParameterManager':
        """ Construct an instance of itself and populate it with either the
        default parameter values or altered values.

        If altered values are given, demands that the amount of values
        is equal to the amount of parameters.
        """
        param_list = list(process_brightway_parameters())

        ppm = cls()
        if scenario_values:
            scenario = list(scenario_values)
            assert len(param_list) == len(scenario)
            ppm.param_values = replace_amounts(param_list, scenario)
        else:
            ppm.param_values = param_list
        return ppm

    @staticmethod
    def _static(data: dict, needed: set) -> dict:
        """ Similar to the `static` method for each Parameter class where the
        ``needed`` variable is a set of the keys actually needed from ``data``.
        """
        return {k: data[k] for k in data.keys() & needed}

    @staticmethod
    def _prune_result_data(data: dict) -> dict:
        """ Takes a str->dict dictionary and extracts the amount field from
        the dictionary.
        """
        return {k: v.get("amount") for k, v in data.items()}

    def recalculate_project_parameters(self) -> Optional[dict]:
        new_values = self.get_altered_values("project")

        data = ProjectParameter.load()
        if not data:
            return

        for name, amount in new_values.items():
            data[name]["amount"] = amount

        ParameterSet(data).evaluate_and_set_amount_field()
        return self._prune_result_data(data)

    def recalculate_database_parameters(self, database: str, global_params: dict = None) -> Optional[dict]:
        new_values = self.get_altered_values(database)
        if global_params is None:
            global_params = {}

        data = DatabaseParameter.load(database)
        if not data:
            return

        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(global_params)
        if missing:
            raise MissingName("The following variables aren't defined:\n{}".format("|".join(missing)))

        glo = self._static(global_params, needed=new_symbols) if new_symbols else None

        ParameterSet(data, glo).evaluate_and_set_amount_field()
        return self._prune_result_data(data)

    def recalculate_activity_parameters(self, group: str, global_params: dict = None) -> Optional[dict]:
        new_values = self.get_altered_values(group)
        if global_params is None:
            global_params = {}

        data = ActivityParameter.load(group)
        if not data:
            return

        for name, amount in new_values.items():
            data[name]["amount"] = amount

        new_symbols = get_new_symbols(data.values(), set(data))
        missing = new_symbols.difference(global_params)
        if missing:
            raise MissingName("The following variables aren't defined:\n{}".format("|".join(missing)))

        glo = self._static(global_params, needed=new_symbols) if new_symbols else None

        ParameterSet(data, glo).evaluate_and_set_amount_field()
        return self._prune_result_data(data)

    @staticmethod
    def recalculate_exchanges(group: str, global_params: dict = None) -> List[Tuple[int, float]]:
        """ Constructs a list of exc.id/amount tuples for the
        ParameterizedExchanges in the given group.
        """
        if global_params is None:
            global_params = {}

        params = (ParameterizedExchange.select()
                  .where(ParameterizedExchange.group == group))

        if not params.exists():
            return []

        interpreter = Interpreter()
        interpreter.symtable.update(global_params)
        return [(p.exchange, interpreter(p.formula)) for p in params]

    def recalculate_scenario(self, scenario_values: Iterable[float]) -> (np.ndarray, np.ndarray):
        """ Convenience function that takes new parameter values and returns
        a fully-formed set of exchange amounts and indices.

        All parameter types are recalculated in turn before interpreting the
        ParameterizedExchange formulas into amounts.
        """
        self.param_values = replace_amounts(self.param_values, scenario_values)
        global_project = self.recalculate_project_parameters()
        all_db = {}
        for p in DatabaseParameter.select(DatabaseParameter.database).distinct():
            db = self.recalculate_database_parameters(p.database, global_project)
            all_db[p.database] = {x: y for x, y in db.items()} if db else {}

        complete_data = []
        complete_indices = []

        for p in ActivityParameter.select(ActivityParameter.group, ActivityParameter.database).distinct():
            combination = {x: y for x, y in global_project.items()}
            combination.update(all_db.get(p.database, {}))
            act = self.recalculate_activity_parameters(p.group, combination)
            combination.update(act)

            # `data` contains the recalculated amounts for the exchanges.
            ids, data = zip(*self.recalculate_exchanges(p.group, global_params=combination))
            indices = []
            for pk in ids:
                exc = ExchangeDataset.get_by_id(pk)
                input_key = (exc.input_database, exc.input_code)
                output_key = (exc.output_database, exc.output_code)
                if exc.input_database == bw.config.biosphere:
                    indices.append((input_key, output_key))
                else:
                    indices.append((input_key, output_key, "technosphere"))
            complete_data.extend(data)
            complete_indices.extend(indices)

        # After recalculating all the exchanges and adding all samples and indices
        # to lists, format them according to presamples requirements:
        # eg: samples as a column of floats and indices as a row of tuples.
        samples = np.array(complete_data)
        samples = samples.reshape(1, -1).T
        indices = np.array(complete_indices)
        return samples, indices

    def presamples_from_scenarios(self, name: str, scenarios: Iterable[Tuple[str, Iterable]]) -> (str, str):
        """ When given a iterable of multiple parameter scenarios, construct
        a presamples package with all of the recalculated exchange amounts.
        """
        sample_data, indice_data = zip(*(self.recalculate_scenario(values) for _, values in scenarios))
        samples = np.concatenate(sample_data, axis=1)
        indices = next(iter(indice_data))

        arrays = ps.split_inventory_presamples(samples, indices)
        ps_id, ps_path = ps.create_presamples_package(
            matrix_data=arrays, name=name, seed="sequential"
        )
        return ps_id, ps_path

    @staticmethod
    def store_presamples_as_resource(name: str, path: str) -> Optional[ps.PresampleResource]:
        if not name or not path:
            return
        resource = ps.PresampleResource.create(name=name, path=path)
        return resource


def process_brightway_parameters() -> Iterable[tuple]:
    """ Converts brightway parameters of all types into a simple structure
    in order of possible dependency.
    """
    return itertools.chain(
        ((p.name, "project", p.amount) for p in ProjectParameter.select()),
        ((p.name, p.database, p.amount) for p in DatabaseParameter.select()),
        ((p.name, p.group, p.amount) for p in ActivityParameter.select())
    )


def replace_amounts(parameters: Iterable[tuple], amounts: Iterable[float]) -> Iterable[tuple]:
    """ Specifically does not check for the length of both values to
    allow the use of generators.
    """
    return (
        (n, g, amount) for ((n, g, _), amount) in zip(parameters, amounts)
    )
