# -*- coding: utf-8 -*-
from typing import Iterable, Optional

from bw2calc.indexing import index_with_arrays
from bw2calc.matrices import TechnosphereBiosphereMatrixBuilder as MB
import numpy as np
import pandas as pd

from ..multilca import MLCA, Contributions
from .dataframe import scenario_names_from_df
from .presamples import build_arrays_from_df, process_arrays_to_package


class SuperstructureMLCA(MLCA):
    """Very similar implementation as the PresamplesMLCA class, a possible
    replacement for using presamples by avoiding saving anything to files.
    """
    def __init__(self, cs_name: str, df: pd.DataFrame):
        assert not df.empty, "Cannot run analysis without data."
        self.scenario_names = scenario_names_from_df(df)
        self.total = len(self.scenario_names)
        assert self.total > 0, "Cannot run analysis without scenarios"

        super().__init__(cs_name)

        # Convert the dataframe into numpy arrays ready for presample conversion
        # This can take a while with big dataframes.
        indices, values = build_arrays_from_df(df)
        self.matrix_data = process_arrays_to_package(indices, values)
        self.index_arrays()  # Actually fill out the correct rows/cols

        # Construct an index dictionary similar to fu_index and method_index
        self._current_index = 0
        self.presamples_index = {k: i for i, k in enumerate(self.scenario_names)}

        # Rebuild numpy arrays with presample dimension included.
        self.lca_scores = np.zeros((len(self.func_units), len(self.methods), self.total))
        self.elementary_flow_contributions = np.zeros((
            len(self.func_units), len(self.methods), self.total,
            self.lca.biosphere_matrix.shape[0]
        ))
        self.process_contributions = np.zeros((
            len(self.func_units), len(self.methods), self.total,
            self.lca.technosphere_matrix.shape[0]
        ))

    @property
    def current(self) -> int:
        return self._current_index

    @current.setter
    def current(self, current: int) -> None:
        """ Ensure current index is looped to 0 if end of array is reached.
        """
        self._current_index = current if current < self.total else 0

    def next_scenario(self):
        self.update_matrices()
        self.current += 1

    def set_scenario(self, index: int) -> None:
        """ Set the current scenario index given a new index to go to
        """
        steps = self._get_steps_to_index(index)
        # self.current = steps[-1] + 1  # Walk the steps to the new index
        for _ in steps:
            self.next_scenario()

    def index_arrays(self):
        """Add row and column values to the indices.

        Copied from the PackagesDataLoader class.
        """
        for samples, indices, metadata in self.matrix_data:
            # Allow for iterative indexing, starting with inventory
            if metadata.get("indexed"):
                # Already indexed
                continue
            elif not hasattr(self.lca, metadata["row dict"]):
                # This dictionary not yet built
                continue
            elif "col dict" in metadata and not hasattr(self.lca, metadata["col dict"]):
                # This dictionary not yet built
                continue

            index_with_arrays(
                indices[metadata["row from label"]],
                indices[metadata["row to label"]],
                getattr(self.lca, metadata["row dict"])
            )
            if "col dict" in metadata:
                index_with_arrays(
                    indices[metadata["col from label"]],
                    indices[metadata["col to label"]],
                    getattr(self.lca, metadata["col dict"])
                )
            metadata["indexed"] = True

    def update_matrices(self) -> None:
        """A rough copy of the `PackagesDataLoader.update_matrices` method."""
        for samples, indices, metadata in self.matrix_data:
            try:
                matrix = getattr(self.lca, metadata["matrix"])
            except AttributeError:
                # This LCA doesn't have this matrix
                continue

            if metadata["matrix"] == "technosphere_matrix":
                # Remove existing matrix factorization
                # because changing technosphere
                if hasattr(self.lca, "solver"):
                    delattr(self.lca, "solver")

            sample = samples[:, self.current]
            if metadata['type'] == "technosphere":
                MB.fix_supply_use(indices, sample)
            if "col dict" in metadata:
                rows = indices[metadata['row to label']]
                cols = indices[metadata['col to label']]
                matrix[rows, cols] = sample
            else:
                matrix[
                    indices[metadata["row to label"]],
                    indices[metadata["row to label"]],
                ] = sample

    def _perform_calculations(self):
        """ Near copy of `MLCA` class, but includes a loop for all presample
        arrays.
        """
        for ps_col in range(self.total):
            self.next_scenario()
            for row, func_unit in enumerate(self.func_units):
                self.lca.redo_lci(func_unit)
                self.scaling_factors.update({
                    (str(func_unit), ps_col): self.lca.supply_array
                })
                self.technosphere_flows.update({
                    (str(func_unit), ps_col): np.multiply(
                        self.lca.supply_array, self.lca.technosphere_matrix.diagonal()
                    )
                })
                self.inventory.update({
                    (str(func_unit), ps_col): np.array(self.lca.inventory.sum(axis=1)).ravel()
                })
                self.inventories.update({
                    (str(func_unit), ps_col): self.lca.inventory
                })

                for col, cf_matrix in enumerate(self.method_matrices):
                    self.lca.characterization_matrix = cf_matrix
                    self.lca.lcia_calculation()
                    self.lca_scores[row, col, ps_col] = self.lca.score
                    self.characterized_inventories[(row, col, ps_col)] = self.lca.characterized_inventory.copy()
                    self.elementary_flow_contributions[row, col, ps_col] = np.array(
                        self.lca.characterized_inventory.sum(axis=1)).ravel()
                    self.process_contributions[row, col, ps_col] = self.lca.characterized_inventory.sum(axis=0)

    def get_results_for_method(self, index: int = 0) -> pd.DataFrame:
        """ Overrides the parent and returns a dataframe with the scenarios
         as columns
        """
        data = self.lca_scores[:, index, :]
        return pd.DataFrame(
            data, index=self.func_key_list, columns=self.scenario_names
        )

    def _get_steps_to_index(self, index: int) -> list:
        """ Determine how many steps to take when given the index we want
         to land on.

        We can only iterate through the presample arrays in one direction, so
         if we go from 2 to 1 we need to calculate the amount of steps to loop
         around to 1.
        """
        if index < 0:
            raise ValueError("Negative indexes are not allowed")
        elif index >= self.total:
            raise ValueError("Given index is not possible for current presamples dataset")
        if index < self.current:
            return [*range(self.current, self.total), *range(index)]
        else:
            return list(range(self.current, index))


class SuperstructureContributions(Contributions):
    mlca: SuperstructureMLCA

    def __init__(self, mlca):
        if not isinstance(mlca, SuperstructureMLCA):
            raise TypeError("Must pass a SuperstructureMLCA object. Passed: {}".format(type(mlca)))
        super().__init__(mlca)

    def _build_inventory(self, inventory: dict, indices: dict, columns: list,
                         fields: list) -> pd.DataFrame:
        inventory = {k[0]: v for k, v in inventory.items() if k[1] == self.mlca.current}
        return super()._build_inventory(inventory, indices, columns, fields)

    def lca_scores_df(self, normalized: bool = False) -> pd.DataFrame:
        """Returns a metadata-annotated DataFrame of the LCA scores.
        """
        scores = self.mlca.lca_scores_normalized if normalized else self.mlca.lca_scores
        scores = scores[:, :, self.mlca.current]
        return super()._build_lca_scores_df(
            scores, self.mlca.fu_activity_keys, self.mlca.methods, self.act_fields
        )

    def _build_contributions(self, data: np.ndarray, index: int, axis: int) -> np.ndarray:
        data = data[:, :, self.mlca.current]
        return super()._build_contributions(data, index, axis)

    @staticmethod
    def _build_scenario_contributions(data: np.ndarray, fu_index: int, m_index: int) -> np.ndarray:
        return data[fu_index, m_index, :]

    def get_contributions(self, contribution, functional_unit=None,
                          method=None) -> np.ndarray:
        """Return a contribution matrix given the type and fu / method

        Allow for both fu and method to exist.
        """
        if not any([functional_unit, method]):
            raise ValueError(
                "Either functional unit, method or both should be given. Provided:"
                "\n Functional unit: {} \n Method: {}".format(functional_unit, method)
            )
        dataset = {
            'process': self.mlca.process_contributions,
            'elementary_flow': self.mlca.elementary_flow_contributions,
        }
        if method and functional_unit:
            return self._build_scenario_contributions(
                dataset[contribution], self.mlca.func_key_dict[functional_unit],
                self.mlca.method_index[method]
            )
        return super().get_contributions(contribution, functional_unit, method)

    def _contribution_index_cols(self, **kwargs) -> (dict, Optional[Iterable]):
        # If both functional_unit and method are given, return presamples index.
        if all(kwargs.values()):
            return self.mlca.presamples_index, self.act_fields
        else:
            return super()._contribution_index_cols(**kwargs)
