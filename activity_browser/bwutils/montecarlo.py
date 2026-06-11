"""
Monte Carlo LCA via Brightway ``MultiLCA``.

When uncertainty layers are enabled, each iteration stores matrix snapshots for
global sensitivity analysis (GSA):

- ``A_matrices`` / ``B_matrices`` — technosphere and biosphere draws
- ``CF_dict[method]`` — characterization factor vectors per iteration
- ``parameter_data`` — sampled parameter amounts (when Parameters is checked)
"""
from collections import defaultdict
from time import time
from typing import Optional
from loguru import logger

import bw2data as bd
import bw2calc as bc
import numpy as np
import pandas as pd

from activity_browser.bwutils.montecarlo_matrix_utils_patch import apply_matrix_utils_mc_patch
from activity_browser.bwutils.parameters import (
    MonteCarloParameterManager,
    bind_parameter_hook,
)

apply_matrix_utils_mc_patch()  # TODO: remove this patch as soon as bw2data 4.8 is released (it should be fixed there, but test)


class MonteCarloLCA(object):
    """Monte Carlo LCA for multiple reference flows and methods from a calculation setup."""

    def __init__(self, cs_name):
        if cs_name not in bd.calculation_setups:
            raise ValueError("{} is not a known `calculation_setup`.".format(cs_name))

        self.cs_name = cs_name
        self.cs = bd.calculation_setups[cs_name]
        self.seed = None
        self.parameter_mc_manager = None
        self.include_technosphere = True
        self.include_biosphere = True
        self.include_cfs = False
        self.include_parameters = False

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

        # Per-iteration snapshots consumed by sensitivity_analysis.GlobalSensitivityAnalysis
        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_data = defaultdict(dict)

        self.results = list()

    def construct_lca(
        self,
        demands: dict,
        method_config: dict,
        technosphere: bool = True,
        biosphere: bool = True,
        characterization: bool = True,
        seed_override: Optional[int] = None,
    ) -> bc.MultiLCA:
        logger.info(f"Monte Carlo demands: {demands}")
        logger.info(f"Monte Carlo impact categories: {method_config}")
        demands = {
            index: {bd.get_activity(k).id: v for k, v in fu.items()}
            for index, fu in demands.items()
        }
        data_objs = bd.get_multilca_data_objs(
            functional_units=demands,
            method_config=method_config,
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

    def calculate(self, iterations: int = 10, seed: Optional[int] = None, **kwargs):
        """Run Monte Carlo LCA with optional technosphere, biosphere, CF, and parameter uncertainty."""
        start = time()
        self.iterations = iterations
        self.seed = seed or bc.utils.get_seed()
        self.include_technosphere = kwargs.get("technosphere", True)
        self.include_biosphere = kwargs.get("biosphere", True)
        self.include_cfs = kwargs.get("cf", True)
        self.include_parameters = kwargs.get("parameters", False)

        # Parameter amounts are applied in after_matrix_iteration (after matrix draws).
        if self.include_parameters:
            bd.parameters.recalculate()

        self.lca = self.construct_lca(
            demands=self.func_units_multilca,
            method_config={"impact_categories": self.methods},
            technosphere=self.include_technosphere,
            biosphere=self.include_biosphere,
            characterization=self.include_cfs,
            seed_override=self.seed,
        )

        self.parameter_mc_manager = None
        if self.include_parameters:
            self.parameter_mc_manager = MonteCarloParameterManager(seed=self.seed)
            bind_parameter_hook(self.lca, self)

        self.lca.lci()
        self.lca.lcia()
        # Always sample iteration 0; do not reuse the deterministic baseline matrices.
        self.lca.keep_first_iteration_flag = False

        self.results = np.zeros((iterations, len(self.func_units), len(self.methods)))

        self.A_matrices = list()
        self.B_matrices = list()
        self.CF_dict = defaultdict(list)
        self.parameter_data = defaultdict(dict)
        if self.parameter_mc_manager is not None:
            self.parameter_data = self.parameter_mc_manager.init_gsa_parameter_data()

        for iteration in range(iterations):
            next(self.lca)

            # Copy sparse matrices: MultiLCA updates technosphere/biosphere in place each iteration.
            self.A_matrices.append(self.lca.technosphere_matrix.copy())
            self.B_matrices.append(self.lca.biosphere_matrix.copy())

            if self.include_cfs:
                for method in self.methods:
                    cf_mm = self.lca.characterization_mm_dict[method]
                    self.CF_dict[method].append(cf_mm.input_data_vector())

            if self.parameter_mc_manager is not None:
                self.parameter_mc_manager.populate_gsa_parameter_data(self.parameter_data)

            for row, func_unit in self.func_units_multilca.items():
                for col, m in enumerate(self.methods):
                    self.results[iteration, int(row), col] = self.lca.scores[(m, row)]

        logger.info(
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
            logger.info(f"Activity key provided: {act_key} {act_index}")
        if method:
            method_index = self.method_index.get(method)
            logger.info(f"Method provided: {method} {method_index}")

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
        if max_length is not None:
            from activity_browser.bwutils.commontasks import wrap_text

            translated_keys = [
                wrap_text(label, max_length=max_length) for label in translated_keys
            ]
        return translated_keys


def perform_MonteCarlo_LCA(
    project="default", cs_name=None, iterations=10, **calculate_kwargs
):
    """Perform Monte Carlo LCA for a calculation setup and return the ``MonteCarloLCA`` instance."""
    logger.info(f"-- Monte Carlo LCA --\n Project: {project} CS: {cs_name}")
    bd.projects.set_current(project, update=False)

    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=iterations, **calculate_kwargs)
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
