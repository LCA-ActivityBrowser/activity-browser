# -*- coding: utf-8 -*-
from time import time
from typing import Optional, Union

import brightway2 as bw
from bw2calc.utils import get_seed
import numpy as np
import pandas as pd
from stats_arrays import MCRandomNumberGenerator
from collections import defaultdict

from .manager import MonteCarloParameterManager


class MonteCarloLCA(object):
    """A Monte Carlo LCA for multiple functional units and methods loaded from a calculation setup."""
    def __init__(self, cs_name):
        if cs_name not in bw.calculation_setups:
            raise ValueError(
                "{} is not a known `calculation_setup`.".format(cs_name)
            )

        self.cs_name = cs_name
        self.cs = bw.calculation_setups[cs_name]
        self.seed = None
        self.cf_rngs = {}
        self.CF_rng_vectors = {}
        self.include_technosphere = True
        self.include_biosphere = True
        self.include_cfs = True
        self.include_parameters = True
        self.param_rng = None
        self.param_cols = ["row", "col", "type"]

        self.tech_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None
        self.bio_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None
        self.cf_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None

        # functional units
        self.func_units = self.cs['inv']
        self.rev_fu_index = {i: fu for i, fu in enumerate(self.func_units)}

        # activities
        self.activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.activity_index = {key: index for index, key in enumerate(self.activity_keys)}
        self.rev_activity_index = {index: key for index, key in enumerate(self.activity_keys)}
        # previously: self.rev_activity_index = {v: k for k, v in self.activity_keys}
        # self.fu_index = {k: i for i, k in enumerate(self.activity_keys)}

        # methods
        self.methods = self.cs['ia']
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {i: m for i, m in enumerate(self.methods)}
        # previously: self.rev_method_index = {v: k for k, v in self.method_index.items()}
        # self.rev_method_index = {v: k for k, v in self.method_index.items()}

        # todo: get rid of the below
        self.func_unit_translation_dict = {str(bw.get_activity(list(func_unit.keys())[0])): func_unit
                                           for func_unit in self.func_units}
        self.func_key_dict = {m: i for i, m in enumerate(self.func_unit_translation_dict.keys())}
        self.func_key_list = list(self.func_key_dict.keys())

        # GSA calculation variables
        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_exchanges = list()
        self.parameters = list()

        self.results = list()

        self.lca = bw.LCA(demand=self.func_units_dict, method=self.methods[0])

    def unify_param_exchanges(self, data: np.ndarray) -> np.ndarray:
        """Convert an array of parameterized exchanges from input/output keys
        into row/col values using dicts generated in bw.LCA object.
        """
        def key_to_rowcol(x) -> tuple:
            if x["type"] in [0, 1]:
                row = self.lca.activity_dict[x["input"]]
                col = self.lca.product_dict[x["output"]]
            else:
                row = self.lca.biosphere_dict[x["input"]]
                col = self.lca.activity_dict[x["output"]]
            return row, col, x["type"], x["amount"]

        unified = np.zeros(data.shape[0], dtype=[
            ('row', '<u4'), ('col', '<u4'), ('type', 'u1'), ('amount', '<f4')
        ])
        for i, d in enumerate(data):
            unified[i] = key_to_rowcol(d)
        return unified

    def load_data(self) -> None:
        """Constructs the random number generators for all of the matrices that
        can be altered by uncertainty.

        If any of these uncertain calculations are not included, the initial
        amounts of the 'params' matrices are used in place of generating
        a vector
        """
        self.lca.load_lci_data()

        self.tech_rng = MCRandomNumberGenerator(self.lca.tech_params, seed=self.seed) \
            if self.include_technosphere else self.lca.tech_params["amount"].copy()
        self.bio_rng = MCRandomNumberGenerator(self.lca.bio_params, seed=self.seed) \
            if self.include_biosphere else self.lca.bio_params["amount"].copy()

        if self.lca.lcia:
            self.cf_rngs = {}  # we need as many cf_rng as impact categories, because they are of different size
            for m in self.methods:
                self.lca.switch_method(m)
                self.lca.load_lcia_data()
                self.cf_rngs[m] = MCRandomNumberGenerator(self.lca.cf_params, seed=self.seed) \
                    if self.include_cfs else self.lca.cf_params["amount"].copy()
        # Construct the MC parameter manager
        if self.include_parameters:
            self.param_rng = MonteCarloParameterManager(seed=self.seed)

        self.lca.activity_dict_rev, self.lca.product_dict_rev, self.lca.biosphere_dict_rev = self.lca.reverse_dict()

    def calculate(self, iterations=10, seed: int = None, **kwargs):
        """Main calculate method for the MC LCA class, allows fine-grained control
        over which uncertainties are included when running MC sampling.
        """
        start = time()
        self.iterations = iterations
        self.seed = seed or get_seed()
        self.include_technosphere = kwargs.get("technosphere", True)
        self.include_biosphere = kwargs.get("biosphere", True)
        self.include_cfs = kwargs.get("cf", True)
        self.include_parameters = kwargs.get("parameters", True)

        self.load_data()

        self.results = np.zeros((iterations, len(self.func_units), len(self.methods)))

        # Reset GSA variables to empty.
        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_exchanges = list()
        self.parameters = list()

        for iteration in range(iterations):
            tech_vector = self.tech_rng.next() if self.include_technosphere else self.tech_rng
            bio_vector = self.bio_rng.next() if self.include_biosphere else self.bio_rng
            if self.include_parameters:
                # Convert the input/output keys into row/col keys, and then match them against
                # the tech_ and bio_params
                data = self.param_rng.next()
                param_exchanges = self.unify_param_exchanges(data)

                # Select the A/B matrix subsets, generate an index and apply
                # the updated exchange values to the respective vectors.
                # Make sure to order the subset so that amounts are inserted
                # at the correct locations.
                subset = param_exchanges[np.isin(param_exchanges["type"], [0, 1])]
                idx = np.argwhere(
                    np.isin(self.lca.tech_params[self.param_cols], subset[self.param_cols])
                ).flatten()
                uniq = np.unique(self.lca.tech_params[idx][["row", "col"]])
                sort_idx = np.searchsorted(uniq, subset[["row", "col"]])
                tech_vector[idx] = subset[sort_idx]["amount"]
                subset = param_exchanges[param_exchanges["type"] == 2]
                idx = np.argwhere(
                    np.isin(self.lca.bio_params[self.param_cols], subset[self.param_cols])
                ).flatten()
                uniq = np.unique(self.lca.bio_params[idx][["row", "col"]])
                sort_idx = np.searchsorted(uniq, subset[["row", "col"]])
                bio_vector[idx] = subset[sort_idx]["amount"]

                # Store parameter data if they are being considered.
                self.parameter_exchanges.append(param_exchanges)
                self.parameters.append(self.param_rng.parameters.to_gsa())

            self.lca.rebuild_technosphere_matrix(tech_vector)
            self.lca.rebuild_biosphere_matrix(bio_vector)

            # store matrices for GSA
            self.A_matrices.append(self.lca.technosphere_matrix)
            self.B_matrices.append(self.lca.biosphere_matrix)

            if not hasattr(self.lca, "demand_array"):
                self.lca.build_demand_array()
            self.lca.lci_calculation()

            # pre-calculating CF vectors enables the use of the SAME CF vector for each FU in a given run
            cf_vectors = {}
            for m in self.methods:
                cf_vectors[m] = self.cf_rngs[m].next() if self.include_cfs else self.cf_rngs[m]
                # store CFs for GSA (in a list defaultdict)
                self.CF_dict[m].append(cf_vectors[m])

            # iterate over FUs
            for row, func_unit in self.rev_fu_index.items():
                self.lca.redo_lci(func_unit)  # lca calculation

                # iterate over methods
                for col, m in self.rev_method_index.items():
                    self.lca.switch_method(m)
                    self.lca.rebuild_characterization_matrix(cf_vectors[m])
                    self.lca.lcia_calculation()
                    self.results[iteration, row, col] = self.lca.score

        print('Monte Carlo LCA: finished {} iterations for {} functional units and {} methods in {} seconds.'.format(
            iterations,
            len(self.func_units),
            len(self.methods),
            np.round(time() - start, 2)
        ))

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

        if not self.results.any():
            raise ValueError('You need to perform a Monte Carlo Simulation first.')
            return None

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

        if not self.results.any():
            raise ValueError('You need to perform a Monte Carlo Simulation first.')
            return None

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


def perform_MonteCarlo_LCA(project='default', cs_name=None, iterations=10):
    """Performs Monte Carlo LCA based on a calculation setup and returns the
    Monte Carlo LCA object."""
    print('-- Monte Carlo LCA --\n Project:', project, 'CS:', cs_name)
    bw.projects.set_current(project)

    # perform Monte Carlo simulation
    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=iterations)
    return mc


if __name__ == "__main__":
    mc = perform_MonteCarlo_LCA(project='ei34', cs_name='kraft paper', iterations=15)

    # test the get_results_by() method
    print('\nTesting the get_results_by() method')
    act_key = mc.activity_keys[0]
    method = mc.methods[0]
    print(mc.get_results_by(act_key=act_key, method=method))
    #    print(mc.get_results_by(act_key=act_key, method=None))
    #    print(mc.get_results_by(act_key=None, method=method))
    #    print(mc.get_results_by(act_key=None, method=None))

    # testing the dataframe output
    print(mc.get_results_dataframe(method=mc.methods[0]))
    print(mc.get_results_dataframe(act_key=mc.activity_keys[0]))