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

from activity_browser.bwutils.multilca import _load_cs, databases_for_fu_keys
from activity_browser.bwutils.montecarlo_matrix_utils_patch import apply_matrix_utils_mc_patch
from activity_browser.bwutils.montecarlo_scenarios import (
    apply_scenario_amounts,
    prepare_scenario_arrays,
)
from activity_browser.bwutils.parameters import (
    MonteCarloParameterManager,
    bind_parameter_hook,
)

apply_matrix_utils_mc_patch()  # TODO: remove this patch as soon as bw2data 4.8 is released (it should be fixed there, but test)


class MonteCarloLCA(object):
    """Monte Carlo LCA for multiple reference flows and methods from a calculation setup."""

    def __init__(self, cs_name, cs: dict | None = None):
        if cs_name not in bd.calculation_setups and cs is None:
            raise ValueError("{} is not a known `calculation_setup`.".format(cs_name))

        self.cs_name = cs_name
        self.cs = cs if cs is not None else bd.calculation_setups[cs_name]
        self.seed = None
        self.parameter_mc_manager = None
        self.include_technosphere = True
        self.include_biosphere = True
        self.include_cfs = False
        self.include_parameters = False
        self.last_run_scenario = None
        self.last_run_includes = None

        _load_cs(self, self.cs["inv"], self.cs["ia"])
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

    def calculate(
        self,
        iterations: int = 10,
        seed: Optional[int] = None,
        scenario_df: Optional[pd.DataFrame] = None,
        scenario: Optional[str | int] = None,
        **kwargs,
    ):
        """Run Monte Carlo LCA with optional technosphere, biosphere, CF, parameter, and scenario amounts."""
        start = time()
        self.iterations = iterations
        self.seed = seed or bc.utils.get_seed()
        self.include_technosphere = kwargs.get("technosphere", True)
        self.include_biosphere = kwargs.get("biosphere", True)
        self.include_cfs = kwargs.get("cf", True)
        self.include_parameters = kwargs.get("parameters", False)
        self.last_run_scenario = None
        self.last_run_includes = None

        scenario_name = None
        scenario_indices = None
        scenario_amounts = None
        if scenario_df is not None:
            scenario_name, scenario_indices, scenario_amounts = prepare_scenario_arrays(
                scenario_df,
                databases_for_fu_keys(self.fu_activity_keys),
                scenario,
            )

        # Parameter amounts are applied in after_matrix_iteration (after matrix draws).
        if self.include_parameters:
            bd.parameters.recalculate()

        self.lca = self.construct_lca(
            demands=self.fu_demands,
            method_config={"impact_categories": self.methods},
            technosphere=self.include_technosphere,
            biosphere=self.include_biosphere,
            characterization=self.include_cfs,
            seed_override=self.seed,
        )

        self.parameter_mc_manager = None
        if self.include_parameters:
            self.parameter_mc_manager = MonteCarloParameterManager(seed=self.seed)

        before_parameters = None
        if scenario_indices is not None and len(scenario_indices):

            def apply_scenario(lca: bc.MultiLCA) -> None:
                apply_scenario_amounts(
                    lca,
                    scenario_indices,
                    scenario_amounts,
                    include_technosphere=self.include_technosphere,
                    include_biosphere=self.include_biosphere,
                )

            before_parameters = apply_scenario

        if before_parameters is not None or self.include_parameters:
            bind_parameter_hook(
                self.lca, self, before_parameters=before_parameters
            )

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

            for row, func_unit in self.fu_demands.items():
                for col, m in enumerate(self.methods):
                    self.results[iteration, int(row), col] = self.lca.scores[(m, row)]

        logger.info(
            f"Monte Carlo LCA: finished {iterations} iterations for {len(self.func_units)} reference flows and "
            f"{len(self.methods)} methods in {np.round(time() - start, 2)} seconds."
        )

        self.last_run_scenario = scenario_name
        self.last_run_includes = {
            "technosphere": self.include_technosphere,
            "biosphere": self.include_biosphere,
            "cf": self.include_cfs,
            "parameters": self.include_parameters,
        }

    @property
    def last_run_summary(self) -> Optional[dict]:
        """Metadata from the last successful ``calculate`` call, or ``None``."""
        if self.last_run_includes is None:
            return None
        return {
            "scenario": self.last_run_scenario,
            "iterations": self.iterations,
            "seed": self.seed,
            "includes": self.last_run_includes,
        }

    @property
    def func_units_dict(self) -> dict:
        """Return a dictionary of reference flows (key, demand)."""
        return {key: 1 for func_unit in self.func_units for key in func_unit}

    def get_results_by(self, fu_row=None, method=None):
        """Slice Monte Carlo results by ``inv`` row index and/or impact method."""
        if not self.results.any():
            raise ValueError("You need to perform a Monte Carlo Simulation first.")

        fu_index = int(fu_row) if fu_row is not None else None
        method_index = self.method_index.get(method) if method else None

        if fu_index is None and method_index is None:
            return self.results
        if fu_index is not None and method_index is None:
            return np.squeeze(self.results[:, fu_index, :])
        if method_index is not None and fu_index is None:
            return np.squeeze(self.results[:, :, method_index])
        return np.squeeze(self.results[:, fu_index, method_index])

    def get_results_dataframe(self, fu_row=None, method=None, labelled=True):
        """DataFrame of MC runs for all reference flows (one method) or all methods (one row)."""
        if not self.results.any():
            raise ValueError("You need to perform a Monte Carlo Simulation first.")

        if (fu_row is not None and method is not None) or (
            fu_row is None and method is None
        ):
            raise ValueError("Must provide fu_row or method, but not both.")

        data = self.get_results_by(fu_row=fu_row, method=method)
        labels = self.fu_keys if method is not None else self.methods
        df = pd.DataFrame(data, columns=labels)

        if labelled and method is not None:
            df.columns = list(self.fu_labels.values())
        elif labelled and fu_row is not None:
            df.columns = list(self.method_labels.values())

        return df


def perform_MonteCarlo_LCA(
    project="default", cs_name=None, iterations=10, **calculate_kwargs
):
    """Perform Monte Carlo LCA for a calculation setup and return the ``MonteCarloLCA`` instance."""
    logger.info(f"-- Monte Carlo LCA --\n Project: {project} CS: {cs_name}")
    bd.projects.set_current(project, update=False)

    mc = MonteCarloLCA(cs_name)
    mc.calculate(iterations=iterations, **calculate_kwargs)
    return mc
