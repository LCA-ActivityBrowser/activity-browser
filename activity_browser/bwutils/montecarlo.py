from collections import defaultdict
from time import time
from typing import Optional, Union
from logging import getLogger

import bw2calc as bc
import bw2data as bd
import numpy as np
import pandas as pd
from stats_arrays import MCRandomNumberGenerator

from activity_browser.mod import bw2data as bd

from .manager import MonteCarloParameterManager

log = getLogger(__name__)


class MonteCarloLCA(object):
    """A Monte Carlo LCA for multiple reference flows and methods loaded from a calculation setup."""

    def __init__(self, cs_name):
        if cs_name not in bd.calculation_setups:
            raise ValueError("{} is not a known `calculation_setup`.".format(cs_name))

        self.cs_name = cs_name
        self.cs = bd.calculation_setups[cs_name]
        self.seed = None
        self.cf_rngs = {}
        self.CF_rng_vectors = {}
        self.include_technosphere = True
        self.include_biosphere = True
        self.include_cfs = False
        # Needs substantial rework for BW 2.5
        self.include_parameters = False
        # self.param_rng = None
        self.param_cols = ["row", "col", "type"]

        # self.tech_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None
        # self.bio_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None
        # self.cf_rng: Optional[Union[MCRandomNumberGenerator, np.ndarray]] = None

        # reference flows
        self.func_units = self.cs["inv"]
        self.rev_fu_index = {i: fu for i, fu in enumerate(self.func_units)}
        self.func_units_multilca = {str(i): fu for i, fu in enumerate(self.func_units)}

        # activities
        self.activity_keys = [list(fu.keys())[0] for fu in self.func_units]
        self.activity_index = {
            key: index for index, key in enumerate(self.activity_keys)
        }
        self.rev_activity_index = {
            index: key for index, key in enumerate(self.activity_keys)
        }

        # methods
        self.methods = list(self.cs["ia"])
        self.method_index = {m: i for i, m in enumerate(self.methods)}
        self.rev_method_index = {i: m for i, m in enumerate(self.methods)}

        # GSA calculation variables
        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_exchanges = list()
        self.parameters = list()
        self.parameter_data = defaultdict(dict)

        self.results = list()

        # Not needed - always call .calculate?
        # self.lca = self.construct_lca(
        #     demands=self.func_units,
        #     method_config={"impact_categories": self.methods},
        #     technosphere=self.include_technosphere,
        #     biosphere=self.include_biosphere,
        #     characterization=self.include_cfs,
        # )

    def construct_lca(
        self,
        demands: dict,
        method_config: dict,
        technosphere: bool = True,
        biosphere: bool = True,
        characterization: bool = True,
        seed_override: Optional[int] = None,
    ) -> bc.MultiLCA:
        log.info(f"Monte Carlo demands: {demands}")
        log.info(f"Monte Carlo impact categories: {method_config}")
        demands = {
            index: {bd.get_activity(k).id: v for k, v in fu.items()}
            for index, fu in demands.items()
        }
        data_objs = bd.get_multilca_data_objs(
            functional_units=demands,
            method_config=method_config
        )
        return bc.MultiLCA(
            demands=demands,
            method_config=method_config,
            data_objs=data_objs,
            selective_use={
                "technosphere_matrix": {"use_distributions": technosphere},
                "biosphere_matrix": {"use_distributions": biosphere},
                "characterization_matrix": {"use_distributions": characterization},
            },
            seed_override=seed_override,
        )

    # def unify_param_exchanges(self, data: np.ndarray) -> np.ndarray:
    #     """Convert an array of parameterized exchanges from input/output keys
    #     into row/col values using dicts generated in bw.LCA object.

    #     If any given exchange does not exist in the current LCA matrix,
    #     it will be dropped from the returned array.
    #     """

    #     def key_to_rowcol(x) -> Optional[tuple]:
    #         if x["type"] in [0, 1]:
    #             row = self.lca.activity_dict.get(x["input"], None)
    #             col = self.lca.product_dict.get(x["output"], None)
    #         else:
    #             row = self.lca.biosphere_dict.get(x["input"], None)
    #             col = self.lca.activity_dict.get(x["output"], None)
    #         # if either the row or the column is None, return np.NaN.
    #         if row is None or col is None:
    #             return None
    #         return row, col, x["type"], x["amount"]

    #     # Convert the data and store in a new array, dropping Nones.
    #     converted = (key_to_rowcol(d) for d in data)
    #     unified = np.array(
    #         [x for x in converted if x is not None],
    #         dtype=[("row", "<u4"), ("col", "<u4"), ("type", "u1"), ("amount", "<f4")],
    #     )
    #     return unified

    # def load_data(self) -> None:
    #     """Constructs the random number generators for all of the matrices that
    #     can be altered by uncertainty.

    #     If any of these uncertain calculations are not included, the initial
    #     amounts of the 'params' matrices are used in place of generating
    #     a vector
    #     """
    #     self.lca.load_lci_data()

    #     self.tech_rng = (
    #         MCRandomNumberGenerator(self.lca.tech_params, seed=self.seed)
    #         if self.include_technosphere
    #         else self.lca.tech_params["amount"].copy()
    #     )
    #     self.bio_rng = (
    #         MCRandomNumberGenerator(self.lca.bio_params, seed=self.seed)
    #         if self.include_biosphere
    #         else self.lca.bio_params["amount"].copy()
    #     )

    #     if self.lca.lcia:
    #         self.cf_rngs = (
    #             {}
    #         )  # we need as many cf_rng as impact categories, because they are of different size
    #         for m in self.methods:
    #             self.lca.switch_method(m)
    #             self.lca.load_lcia_data()
    #             self.cf_rngs[m] = (
    #                 MCRandomNumberGenerator(self.lca.cf_params, seed=self.seed)
    #                 if self.include_cfs
    #                 else self.lca.cf_params["amount"].copy()
    #             )
    #     # Construct the MC parameter manager
    #     if self.include_parameters:
    #         self.param_rng = MonteCarloParameterManager(seed=self.seed)

    #     (
    #         self.lca.activity_dict_rev,
    #         self.lca.product_dict_rev,
    #         self.lca.biosphere_dict_rev,
    #     ) = self.lca.reverse_dict()

    def calculate(self, iterations: int = 10, seed: Optional[int] = None, **kwargs):
        """Main calculate method for the MC LCA class, allows fine-grained control
        over which uncertainties are included when running MC sampling.
        """
        start = time()
        self.iterations = iterations
        self.seed = seed or bc.utils.get_seed()
        self.include_technosphere = kwargs.get("technosphere", True)
        self.include_biosphere = kwargs.get("biosphere", True)
        self.include_cfs = kwargs.get("cf", True)
        self.include_parameters = kwargs.get("parameters", True)

        self.lca = self.construct_lca(
            demands=self.func_units_multilca,
            method_config={"impact_categories": self.methods},
            technosphere=self.include_technosphere,
            biosphere=self.include_biosphere,
            characterization=self.include_cfs,
        )
        self.lca.lci()
        self.lca.lcia()
        self.lca.keep_first_iteration_flag = True

        self.results = np.zeros((iterations, len(self.func_units), len(self.methods)))

        # Reset GSA variables to empty.
        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_exchanges = list()
        self.parameters = list()

        # Prepare GSA parameter schema:
        if self.include_parameters:
            raise ValueError("Parameter sampling not currently supported")
            # self.parameter_data = self.param_rng.extract_active_parameters(self.lca)
            # # Add a values field to handle all the sampled parameter values.
            # for k in self.parameter_data:
            #     self.parameter_data[k]["values"] = []

        for iteration in range(iterations):
            next(self.lca)
            # tech_vector = (
            #     self.tech_rng.next() if self.include_technosphere else self.tech_rng
            # )
            # bio_vector = self.bio_rng.next() if self.include_biosphere else self.bio_rng
            # if self.include_parameters:
            #     # Convert the input/output keys into row/col keys, and then match them against
            #     # the tech_ and bio_params
            #     data = self.param_rng.next()
            #     param_exchanges = self.unify_param_exchanges(data)

            #     # Select technosphere subset from param_exchanges.
            #     subset = param_exchanges[np.isin(param_exchanges["type"], [0, 1])]
            #     # Create index of where to insert new values from tech_params array.
            #     idx = np.argwhere(
            #         np.isin(
            #             self.lca.tech_params[self.param_cols], subset[self.param_cols]
            #         )
            #     ).flatten()
            #     # Construct unique array of row+col+type combinations
            #     uniq = np.unique(self.lca.tech_params[idx][self.param_cols])
            #     # Use the unique array to sort the subset (ensures values
            #     # are inserted at the correct index)
            #     sort_idx = np.searchsorted(uniq, subset[self.param_cols])
            #     # Finally, insert the sorted subset amounts into the tech_vector
            #     # at the correct indexes.
            #     tech_vector[idx] = subset[sort_idx]["amount"]
            #     # Repeat the above, but for the biosphere array.
            #     subset = param_exchanges[param_exchanges["type"] == 2]
            #     idx = np.argwhere(
            #         np.isin(
            #             self.lca.bio_params[self.param_cols], subset[self.param_cols]
            #         )
            #     ).flatten()
            #     uniq = np.unique(self.lca.bio_params[idx][self.param_cols])
            #     sort_idx = np.searchsorted(uniq, subset[self.param_cols])
            #     bio_vector[idx] = subset[sort_idx]["amount"]

            #     # Store parameter data for GSA
            #     self.parameter_exchanges.append(param_exchanges)
            #     self.parameters.append(self.param_rng.parameters.to_gsa())
            #     # Extract sampled values for parameters, store.
            #     self.param_rng.retrieve_sampled_values(self.parameter_data)

            # self.lca.rebuild_technosphere_matrix(tech_vector)
            # self.lca.rebuild_biosphere_matrix(bio_vector)

            # store matrices for GSA
            self.A_matrices.append(self.lca.technosphere_matrix)
            self.B_matrices.append(self.lca.biosphere_matrix)

            # if not hasattr(self.lca, "demand_array"):
            #     self.lca.build_demand_array()
            # self.lca.lci_calculation()

            # pre-calculating CF vectors enables the use of the SAME CF vector for each FU in a given run
            # cf_vectors = {}
            # for m in self.methods:
            #     cf_vectors[m] = (
            #         self.cf_rngs[m].next() if self.include_cfs else self.cf_rngs[m]
            #     )
            #     # store CFs for GSA (in a list defaultdict)
            #     self.CF_dict[m].append(cf_vectors[m])

            # iterate over FUs
            # for row, func_unit in self.rev_fu_index.items():
            #     self.lca.redo_lci(func_unit)  # lca calculation

            #     # iterate over methods
            #     for col, m in self.rev_method_index.items():
            #         self.lca.switch_method(m)
            #         self.lca.rebuild_characterization_matrix(cf_vectors[m])
            #         self.lca.lcia_calculation()
            #         self.results[iteration, row, col] = self.lca.score

            for row, func_unit in self.func_units_multilca.items():
                # self.lca.redo_lci(func_unit)  # lca calculation

                # iterate over methods
                for col, m in enumerate(self.methods):
                    # self.lca.switch_method(m)
                    # self.lca.rebuild_characterization_matrix(cf_vectors[m])
                    # self.lca.lcia_calculation()
                    self.results[iteration, int(row), col] = self.lca.scores[(m, row)]

        log.info(
            f"Monte Carlo LCA: finished {iterations} iterations for {len(self.func_units)} reference flows and "
            f"{len(self.methods)} methods in {np.round(time() - start, 2)} seconds."
        )

    @property
    def func_units_dict(self) -> dict:
        """Return a dictionary of reference flows (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    def get_results_by(self, act_key=None, method=None):
        """Get a slice or all of the results.
        - if a method is provided, results will be given for all reference flows and runs
        - if a reference flow is provided, results will be given for all impact categories and runs
        - if a reference flow and impact category is provided, results will be given for all runs of that combination
        - if nothing is given, all results are returned
        """

        if not self.results.any():
            raise ValueError("You need to perform a Monte Carlo Simulation first.")
            return None

        if act_key:
            act_index = self.activity_index.get(act_key)
            log.info(f"Activity key provided: {act_key} {act_index}")
        if method:
            method_index = self.method_index.get(method)
            log.info(f"Method provided: {method} {method_index}")

        if not act_key and not method:
            return self.results
        elif act_key and not method:
            return np.squeeze(self.results[:, act_index, :])
        elif method and not act_key:
            return np.squeeze(self.results[:, :, method_index])
        elif method and act_key:
            return np.squeeze(self.results[:, act_index, method_index])

    def get_results_dataframe(self, act_key=None, method=None, labelled=True):
        """Return a Pandas DataFrame with results for all runs either for
        - all reference flows and a selected impact categories or
        - all impact categories and a selected reference flow.

        If labelled=True, then the activity keys are converted to a human
        readable format.
        """

        if not self.results.any():
            raise ValueError("You need to perform a Monte Carlo Simulation first.")
            return None

        if act_key and method or not act_key and not method:
            raise ValueError("Must provide activity key or method, but not both.")
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
    def get_labels(
        key_list, fields: list = None, separator=" | ", max_length: int = None
    ) -> list:
        fields = fields or ["name", "reference product", "location", "database"]
        # need to do this as the keys come from a pd.Multiindex
        acts = (bd.get_activity(key).as_dict() for key in (k for k in key_list))
        translated_keys = [
            separator.join([act.get(field, "") for field in fields]) for act in acts
        ]
        # if max_length:
        #     translated_keys = [wrap_text(k, max_length=max_length) for k in translated_keys]
        return translated_keys


def perform_MonteCarlo_LCA(project="default", cs_name=None, iterations=10):
    """Performs Monte Carlo LCA based on a calculation setup and returns the
    Monte Carlo LCA object."""
    log.info(f"-- Monte Carlo LCA --\n Project: {project} CS: {cs_name}")
    bd.projects.set_current(project)

    # perform Monte Carlo simulation
    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=iterations)
    return mc


if __name__ == "__main__":
    mc = perform_MonteCarlo_LCA(project="ei34", cs_name="kraft paper", iterations=15)

    # test the get_results_by() method
    #    print('\nTesting the get_results_by() method')
    act_key = mc.activity_keys[0]
    method = mc.methods[0]
#    print(mc.get_results_by(act_key=act_key, method=method))
#    print(mc.get_results_by(act_key=act_key, method=None))
#    print(mc.get_results_by(act_key=None, method=method))
#    print(mc.get_results_by(act_key=None, method=None))

# testing the dataframe output
#    print(mc.get_results_dataframe(method=mc.methods[0]))
#    print(mc.get_results_dataframe(act_key=mc.activity_keys[0]))
