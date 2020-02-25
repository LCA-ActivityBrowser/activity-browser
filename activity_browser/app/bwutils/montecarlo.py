# -*- coding: utf-8 -*-
from time import time

import brightway2 as bw
from bw2calc.utils import get_seed
import numpy as np
import pandas as pd
from stats_arrays import MCRandomNumberGenerator

from .manager import MonteCarloParameterManager


class MCCertainNumberGenerator(MCRandomNumberGenerator):
    """Simple drop-in replacement of the `MCRandomNumberGenerator` to
    avoid a lot of if/else tests.

    Inspired by https://stackoverflow.com/a/54269982
    """
    def __init__(self, params, maximum_iterations=50, seed=None, **kwargs):
        super().__init__(params, maximum_iterations, seed, **kwargs)
        self.values = self.params["amount"]

    def generate(self, samples=1):
        if samples == 1:
            data = self.values.copy()
        else:
            data = np.broadcast_to(self.values, (samples, self.length)).T
        return data


class CSMonteCarloLCA(object):
    """A Monte Carlo LCA for multiple functional units and methods loaded from a calculation setup."""
    def __init__(self, cs_name):
        if cs_name not in bw.calculation_setups:
            raise ValueError(
                "{} is not a known `calculation_setup`.".format(cs_name)
            )

        self.cs_name = cs_name
        cs = bw.calculation_setups[cs_name]
        self.seed = None
        self.cf_rngs = {}
        self.CF_rng_vectors = {}
        self.include_parameters = False
        self.param_rng = None
        self.param_cols = ["input", "output", "type"]

        # functional units
        self.func_units = cs['inv']
        self.rev_fu_index = {i: fu for i, fu in enumerate(self.func_units)}

        # activities
        self.activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.activity_index = {key: index for index, key in enumerate(self.activity_keys)}
        self.rev_activity_index = {v: k for k, v in self.activity_keys}
        # self.fu_index = {k: i for i, k in enumerate(self.activity_keys)}

        # methods
        self.methods = cs['ia']
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {v: k for k, v in self.method_index.items()}

        # todo: get rid of the below
        self.func_unit_translation_dict = {str(bw.get_activity(list(func_unit.keys())[0])): func_unit
                                           for func_unit in self.func_units}
        self.func_key_dict = {m: i for i, m in enumerate(self.func_unit_translation_dict.keys())}
        self.func_key_list = list(self.func_key_dict.keys())

        # todo: get rid of the below
        self.method_dict_list = []
        for i, m in enumerate(self.methods):
            self.method_dict_list.append({m: i})

        self.results = list()

        self.lca = bw.LCA(demand=self.func_units_dict, method=self.methods[0])

    def load_data(self):
        self.lca.load_lci_data()
        self.lca.tech_rng = MCRandomNumberGenerator(self.lca.tech_params, seed=self.seed)
        self.lca.bio_rng = MCRandomNumberGenerator(self.lca.bio_params, seed=self.seed)
        if self.lca.lcia:
            self.cf_rngs = {}  # we need as many cf_rng as impact categories, because they are of different size
            for m in self.methods:
                self.lca.switch_method(m)
                self.lca.load_lcia_data()
                self.cf_rngs[m] = MCRandomNumberGenerator(self.lca.cf_params, seed=self.seed)
        # Construct the MC parameter manager
        if self.include_parameters:
            self.param_rng = MonteCarloParameterManager(seed=self.seed)

    def calculate(self, iterations=10, seed: int = None, parameters: bool = False):
        start = time()
        self.seed = seed or get_seed()
        self.include_parameters = parameters
        self.load_data()
        self.results = np.zeros((iterations, len(self.func_units), len(self.methods)))

        for iteration in range(iterations):
            if not hasattr(self.lca, "tech_rng"):
                self.load_data()

            tech_vector = self.lca.tech_rng.next()
            bio_vector = self.lca.bio_rng.next()
            if self.include_parameters:
                param_exchanges = self.param_rng.next()
                # combination of 'input', 'output', 'type' columns is unique
                # For each recalculated exchange, match it to either matrix and
                # override the value within that matrix.
                for p in param_exchanges:
                    tech_vector[self.lca.tech_params[self.param_cols] == p[self.param_cols]] = p["amount"]
                    bio_vector[self.lca.bio_params[self.param_cols] == p[self.param_cols]] = p["amount"]

            self.lca.rebuild_technosphere_matrix(tech_vector)
            self.lca.rebuild_biosphere_matrix(bio_vector)

            if not hasattr(self.lca, "demand_array"):
                self.lca.build_demand_array()
            self.lca.lci_calculation()

            # pre-calculating CF vectors enables the use of the SAME CF vector for each FU in a given run
            cf_vectors = {}
            for m in self.methods:
                cf_vectors[m] = self.cf_rngs[m].next()

            # lca_scores = np.zeros((len(self.func_units), len(self.methods)))

            # iterate over FUs
            for row, func_unit in self.rev_fu_index.items():
                self.lca.redo_lci(func_unit)  # lca calculation

                # iterate over methods
                for col, m in self.rev_method_index.items():
                    self.lca.switch_method(m)
                    self.lca.rebuild_characterization_matrix(cf_vectors[m])
                    self.lca.lcia_calculation()
                    # lca_scores[row, col] = self.lca.score
                    self.results[iteration, row, col] = self.lca.score

        print('CSMonteCarloLCA: finished {} iterations for {} functional units and {} methods in {} seconds.'.format(
            iterations, len(self.func_units), len(self.methods), time() - start
        ))
            # self.results.append(lca_scores)
            # self.results[(method, func_unit)] = lca_scores

    @property
    def func_units_dict(self) -> dict:
        """Return a dictionary of functional units (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    def get_results_by(self, act_key=None, method=None):
        """Get a slice or all of the results.
        - if a method is provided, results will be given for all functional units and runs
        - if a functional unit is provided, results will be given for all methods and runs
        - if a functional unit and method is provided, results will be given for all runs of that combination
        - if nothing is given, all results are returned
        """
        if act_key:
            act_index = self.activity_index.get(act_key)
            print('Activity key provided:', act_key, act_index)
        if method:
            method_index = self.method_index.get(method)
            print('Method provided', method, method_index)

        if not act_key and not method:
            return self.results
        elif act_key and not method:
            return np.squeeze(self.results[:, act_index, :])
        elif method and not act_key:
            return np.squeeze(self.results[:, :, method_index])
        elif method and act_key:
            print(act_index, method_index)
            return np.squeeze(self.results[:, act_index, method_index])

    def get_results_dataframe(self, act_key=None, method=None, labelled=True):
        """Return a Pandas DataFrame with results for all runs either for
        - all functional units and a selected method or
        - all methods and a selected functional unit.

        If labelled=True, then the activity keys are converted to a human
        readable format.
        """
        if act_key and method or not act_key and not method:
            raise ValueError('Must provide activity key or method, but not both.')
        data = self.get_results_by(act_key=act_key, method=method)

        if method:
            labels = self.activity_keys
        elif act_key:
            labels = self.methods

        df = pd.DataFrame(data, columns=labels)

        # optionally convert activity keys to human readable output
        if labelled and method:
            df.columns = self.get_labels(df.columns, max_length=20)

        return df

    @staticmethod
    def get_labels(key_list, fields: list = None, separator=' | ',
                   max_length: int = None) -> list:
        fields = fields or ['name', 'reference product', 'location', 'database']
        # need to do this as the keys come from a pd.Multiindex
        acts = (bw.get_activity(key).as_dict() for key in (k for k in key_list))
        translated_keys = [
            separator.join([act.get(field, '') for field in fields])
            for act in acts
        ]
        # if max_length:
        #     translated_keys = [wrap_text(k, max_length=max_length) for k in translated_keys]
        return translated_keys


if __name__ == "__main__":
    print(bw.projects)
    bw.projects.set_current('default')
    print(bw.databases)

    cs = bw.calculation_setups['A']
    mc = CSMonteCarloLCA('A')
    mc.calculate(iterations=5)

    # test the get_results_by() method
    print('Testing the get_results_by() method')
    act_key = mc.activity_keys[0]
    method = mc.methods[0]
    print(mc.get_results_by(act_key=act_key, method=method))
    print(mc.get_results_by(act_key=act_key, method=None))
    print(mc.get_results_by(act_key=None, method=method))
    print(mc.get_results_by(act_key=None, method=None))

    # testing the dataframe output
    print(mc.get_results_dataframe(method=mc.methods[0]))
    print(mc.get_results_dataframe(act_key=mc.activity_keys[0]))
