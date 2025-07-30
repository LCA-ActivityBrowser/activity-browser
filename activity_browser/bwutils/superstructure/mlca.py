# -*- coding: utf-8 -*-
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QPushButton

from activity_browser.mod import bw2data as bd
from activity_browser.bwutils import AB_metadata

from ..commontasks import format_activity_label
from ..errors import ScenarioExchangeNotFoundError
from ..multilca import MLCA, Contributions
from ..utils import Index
from .dataframe import (arrays_from_indexed_superstructure,
                        filter_databases_indexed_superstructure,
                        scenario_names_from_df)
from .file_dialogs import ABPopup

try:
    from bw2calc.matrices import TechnosphereBiosphereMatrixBuilder as MB
except ModuleNotFoundError:
    pass  # removed in bw25


class SuperstructureMLCA(MLCA):
    """Subclass of the `MLCA` class which adds another dimension in the form
    of scenarios.
    """

    matrices = {
        "biosphere": "biosphere_matrix",
        "technosphere": "technosphere_matrix",
        "production": "technosphere_matrix",
    }

    def __init__(self, cs_name: str, df: pd.DataFrame):
        assert isinstance(df, pd.DataFrame), (
            "Check if you have provided at least 1 reference flow, 1 impact category "
            "and 1 scenario file. "
        )
        assert not df.empty, "Cannot run analysis without data."
        self.scenario_names = scenario_names_from_df(df)
        self.total = len(self.scenario_names)
        assert self.total > 0, "Cannot run analysis without scenarios"

        super().__init__(cs_name)

        # Scenarios overwrite the lca.xxx_matrix. For supporting absent values
        # in scenario files defaults are required, to prevent these from being
        # overwritten duplicates are required...
        self.default_technosphere_matrix = self.lca.technosphere_matrix.copy()
        self.default_biosphere_matrix = self.lca.biosphere_matrix.copy()
        self.defaults = {
            "technosphere": "default_technosphere_matrix",
            "production": "default_technosphere_matrix",
            "biosphere": "default_biosphere_matrix",
        }

        # Filter dataframe for keys that do not occur in the LCA matrix.
        df = filter_databases_indexed_superstructure(df, self.all_databases)
        assert not df.empty, "Filtering unused flows removed all of the scenario data."

        self.indices, self.values = arrays_from_indexed_superstructure(df)
        # Note: Using the mapping scheme from brightway and presamples,
        # the 'input' keys are matched to the product_dict or
        # biosphere_dict ('rows') while the 'output' keys are matched
        # to the activity_dict ('cols').

        # Side-note on presamples: Presamples was used in AB for calculating scenarios,
        # presamples was superseded by this implementation. For more reading:
        # https://presamples.readthedocs.io/en/latest/use_with_bw2.html
        self.matrix_indices = np.zeros(
            len(self.indices),
            dtype=[
                ("row", np.uint32),
                ("col", np.uint32),
                ("flip", np.bool_),
            ],
        )
        self.indices_to_matrix()

        # Construct an index dictionary similar to fu_index and method_index
        self._current_index = 0
        self.scenario_index = {k: i for i, k in enumerate(self.scenario_names)}

        # Rebuild numpy arrays with scenario dimension included.
        self.lca_scores = np.zeros(
            (len(self.func_units), len(self.methods), self.total)
        )
        self.elementary_flow_contributions = np.zeros(
            (
                len(self.func_units),
                len(self.methods),
                self.total,
                self.lca.biosphere_matrix.shape[0],
            )
        )
        self.process_contributions = np.zeros(
            (
                len(self.func_units),
                len(self.methods),
                self.total,
                self.lca.technosphere_matrix.shape[0],
            )
        )

    @property
    def current(self) -> int:
        return self._current_index

    @current.setter
    def current(self, current: int) -> None:
        """Ensure current index is looped to 0 if end of array is reached."""
        self._current_index = current if current < self.total else 0

    def next_scenario(self):
        self.update_matrices()
        self.current += 1

    def set_scenario(self, index: int) -> None:
        """Set the current scenario index given a new index to go to"""
        steps = self._get_steps_to_index(index)
        # self.current = steps[-1] + 1  # Walk the steps to the new index
        for _ in steps:
            self.next_scenario()

    def indices_to_matrix(self) -> None:
        def convert(idx: Index) -> tuple:
            in_dict = (
                self.lca.biosphere_dict
                if idx.flow_type == "biosphere"
                else self.lca.product_dict
            )
            return (
                in_dict.get(idx.input_id),
                self.lca.activity_dict.get(idx.output_id),
                idx.flip,
            )

        for i, index in enumerate(self.indices):
            try:
                self.matrix_indices[i] = convert(index)
            except (ValueError, KeyError) as e:
                # This is to be used as a fail safe for the case where we don't catch a bad exchange during the import
                # process, or if something else causes an issue with the exchange
                msg = f"One of the activities in the exchange between ({index.input.database}, {index.input.code}) and ({index.output.database}, {index.output.code}) from the scenario file is not present within the designated database. Please check both keys for this exchange within your scenario file with the corresponding databases."
                critical = ABPopup.abCritical(
                    "Scenario Key Error", msg, QPushButton("Cancel")
                )
                critical.exec_()
                raise ScenarioExchangeNotFoundError

    def update_matrices(self) -> None:
        """A Simplified version of the `PackagesDataLoader.update_matrices` method.
        In this case, we expect to only replace technosphere and biosphere
        values, leaving out characterization factor values.
        """
        kinds = set([idx[2] for idx in self.indices])
        types = np.array([idx[2] for idx in self.indices])
        for kind in kinds:
            idx = self.matrix_indices[types == kind]
            sample = self.values[types == kind, self.current]
            # Previously filtered sample and idx for NaN values in samples.
            # Currently replaces sample NaN values with defaults from the databases
            if np.isnan(sample).any():
                default = getattr(self, self.defaults[kind])
                na_idx = idx[np.isnan(sample)]
                if kind == "technosphere":
                    sample[np.isnan(sample)] = np.multiply(
                        default[na_idx["row"], na_idx["col"]].tolist()[0], -1
                    )
                else:
                    sample[np.isnan(sample)] = default[
                        na_idx["row"], na_idx["col"]
                    ].tolist()[0]
            try:
                matrix = getattr(self.lca, self.matrices[kind])
            except AttributeError:
                # This LCA doesn't have this matrix
                continue

            if self.matrices[kind] == "technosphere_matrix":
                # Remove existing matrix factorization
                # because changing technosphere
                if hasattr(self.lca, "solver"):
                    delattr(self.lca, "solver")

            mask = np.where(idx["flip"] == True)
            sample[mask] = -1 * sample[mask]

            matrix[
                idx["row"],
                idx["col"],
            ] = sample

    def _perform_calculations(self):
        """Near copy of `MLCA` class, but includes a loop for all scenarios."""
        for ps_col in range(self.total):
            self.next_scenario()
            for row, func_unit in enumerate(self.func_units):
                try:
                    self.lca.redo_lci(func_unit)
                except:
                    # bw25 compatibility requires activity id instead of activity key
                    key = list(func_unit.keys())[0]
                    self.lca.redo_lci({bd.get_activity(key).id: func_unit[key]})

                self.scaling_factors.update(
                    {(str(func_unit), ps_col): self.lca.supply_array}
                )
                self.technosphere_flows.update(
                    {
                        (str(func_unit), ps_col): np.multiply(
                            self.lca.supply_array,
                            self.lca.technosphere_matrix.diagonal(),
                        )
                    }
                )
                self.inventory.update(
                    {
                        (str(func_unit), ps_col): np.array(
                            self.lca.inventory.sum(axis=1)
                        ).ravel()
                    }
                )
                self.inventories.update({(str(func_unit), ps_col): self.lca.inventory})

                for col, cf_matrix in enumerate(self.method_matrices):
                    self.lca.characterization_matrix = cf_matrix
                    self.lca.lcia_calculation()
                    self.lca_scores[row, col, ps_col] = self.lca.score
                    self.characterized_inventories[(row, col, ps_col)] = (
                        self.lca.characterized_inventory.copy()
                    )
                    self.elementary_flow_contributions[row, col, ps_col] = np.array(
                        self.lca.characterized_inventory.sum(axis=1)
                    ).ravel()
                    self.process_contributions[row, col, ps_col] = (
                        self.lca.characterized_inventory.sum(axis=0)
                    )

    def update_lca_calculation_for_sankey(
        self, scenario_index: int, func_unit: str, method_index: int
    ):
        """
        Reuses the LCA object to prepare the LCA object for necessary calculations to be made before performing the
        Graph Traversal calculations

        @param scenario_index: Index of the Scenario for which the calculation must be performed
        @param func_unit: The functional unit for which the calculation must be performed
        @param method_index: Index of the method for which the calculation must be performed
        """
        self.current = scenario_index
        self.update_matrices()
        try:
            self.lca.redo_lci(func_unit)
        except:
            # brightway25 compatibility
            key = list(func_unit.keys())[0]
            self.lca.redo_lci({bd.get_activity(key).id: func_unit[key]})
        self.lca.characterization_matrix = self.method_matrices[method_index]
        self.lca.lcia_calculation()
        self.lca.decompose_technosphere()

    def get_results_for_method(self, index: int = 0) -> pd.DataFrame:
        """Overrides the parent and returns a dataframe with the scenarios
        as columns
        """
        data = self.lca_scores[:, index, :]
        return pd.DataFrame(data, index=self.func_key_list, columns=self.scenario_names)

    def _get_steps_to_index(self, index: int) -> list:
        """Determine how many steps to take when given the index we want
         to land on.

        We can only iterate through the presample arrays in one direction, so
         if we go from 2 to 1 we need to calculate the amount of steps to loop
         around to 1.
        """
        if index < 0:
            raise ValueError("Negative indexes are not allowed")
        elif index >= self.total:
            raise ValueError("Given index is not possible for current scenario dataset")
        if index < self.current:
            return [*range(self.current, self.total), *range(index)]
        else:
            return list(range(self.current, index))

    def lca_scores_to_dataframe(self) -> pd.DataFrame:
        """Returns a dataframe of LCA scores using FU labels as index and
        the product of methods and scenarios as columns.
        """
        labels = [format_activity_label(k, style="pnld") for k in self.fu_activity_keys]
        methods = [", ".join(m) for m in self.methods]
        df = pd.DataFrame(
            data=[],
            index=pd.Index(labels),
            columns=pd.MultiIndex.from_product(
                [methods, self.scenario_names], names=["method", "scenario"]
            ),
        )
        # Now insert the LCA scores in the correct locations.
        for x, m in enumerate(methods):
            for y, s in enumerate(self.scenario_names):
                idx = pd.MultiIndex.from_tuples([(m, s)])
                df.loc[:, idx] = self.lca_scores[:, x, y]
        return df


class SuperstructureContributions(Contributions):
    mlca: SuperstructureMLCA

    def __init__(self, mlca):
        if not isinstance(mlca, SuperstructureMLCA):
            raise TypeError(
                "Must pass a SuperstructureMLCA object. Passed: {}".format(type(mlca))
            )
        super().__init__(mlca)

    def _build_inventory(
        self, inventory: dict, indices: dict, columns: list, fields: list
    ) -> pd.DataFrame:
        inventory = {k[0]: v for k, v in inventory.items() if k[1] == self.mlca.current}
        return super()._build_inventory(inventory, indices, columns, fields)

    def lca_scores_df(self, normalized: bool = False) -> pd.DataFrame:
        """Returns a metadata-annotated DataFrame of the LCA scores."""
        scores = self.mlca.lca_scores_normalized if normalized else self.mlca.lca_scores
        scores = scores[:, :, self.mlca.current]
        return self._build_lca_scores_df(scores)

    def _build_contributions(
        self, data: np.ndarray, index: int, axis: int
    ) -> np.ndarray:
        data = data[:, :, self.mlca.current]
        return super()._build_contributions(data, index, axis)

    @staticmethod
    def _build_scenario_contributions(
        data: np.ndarray, fu_index: int, m_index: int
    ) -> np.ndarray:
        return data[fu_index, m_index, :]

    def get_contributions(
        self, contribution, functional_unit=None, method=None, scenario=0
    ) -> np.ndarray:
        """Return a contribution matrix given the type and fu / method

        Allow for both fu and method to exist.
        """
        if not any([functional_unit, method]):
            raise ValueError(
                "Either reference flow, impact category or both should be given. Provided:"
                "\n Reference flow: {} \n Impact Category: {}".format(
                    functional_unit, method
                )
            )
        dataset = {
            "process": self.mlca.process_contributions,
            "elementary_flow": self.mlca.elementary_flow_contributions,
        }
        if method and functional_unit:
            return self._build_scenario_contributions(
                dataset[contribution],
                self.mlca.func_key_dict[functional_unit],
                self.mlca.method_index[method],
            )
        self.mlca.current = scenario
        return super().get_contributions(contribution, functional_unit, method)

    def _contribution_index_cols(self, **kwargs) -> (dict, Optional[Iterable]):
        # If both functional_unit and method are given, return scenario index.
        if all(kwargs.values()):
            return self.mlca.scenario_index, self.act_fields
        else:
            return super()._contribution_index_cols(**kwargs)
