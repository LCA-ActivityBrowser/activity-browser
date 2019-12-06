# -*- coding: utf-8 -*-
from ast import literal_eval
from typing import Iterable, List, Optional

import brightway2 as bw
import numpy as np
import pandas as pd
import presamples as ps

from ..multilca import MLCA, Contributions
from .utils import get_package_path


class PresamplesMLCA(MLCA):
    """ Subclass of the `MLCA` class which adds another dimension in the form
     of scenarios / presamples arrays.

    The initial calculation will take use the first presamples array.
    After this, each call to `calculate_scenario` will update the inventory
     matrices and recalculate the results.
    """
    def __init__(self, cs_name: str, ps_name: str):
        self.package = ps.PresamplesPackage(get_package_path(ps_name))
        self.resource = ps.PresampleResource.get_or_none(name=self.package.name)
        if not self.package:
            raise ValueError("Presamples package with name or id '{}' not found.".format(ps_name))
        super().__init__(cs_name)
        self.total = self.package.ncols
        self._current_index = 0

        # Construct an index dictionary similar to fu_index and method_index
        self.presamples_index = {k: i for i, k in enumerate(self.get_scenario_names())}

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
        self.lca.presamples.update_matrices(self.lca)
        self.current += 1

    def set_scenario(self, index: int) -> None:
        """ Set the current scenario index given a new index to go to
        """
        steps = self._get_steps_to_index(index)
        # self.current = steps[-1] + 1  # Walk the steps to the new index
        for _ in steps:
            self.next_scenario()

    def _construct_lca(self) -> bw.LCA:
        return bw.LCA(
            demand=self.func_units_dict, method=self.methods[0],
            presamples=[self.package.path]
        )

    def _perform_calculations(self):
        """ Near copy of `MLCA` class, but includes a loop for all presample
        arrays.
        """
        for ps_col in range(self.total):
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
            self.next_scenario()

    def get_results_for_method(self, index: int = 0) -> pd.DataFrame:
        """ Overrides the parent and returns a dataframe with the scenarios
         as columns
        """
        data = self.lca_scores[:, index, :]
        return pd.DataFrame(
            data, index=self.func_key_list, columns=self.get_scenario_names()
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

    def get_scenario_names(self) -> List[str]:
        description = self.resource.description if self.resource else None
        if description is None:
            return ["Scenario{}".format(i) for i in range(self.total)]
        # Attempt to convert the string description
        try:
            literal = literal_eval(description)
            if isinstance(literal, (tuple, list, dict)):
                return list(literal)
            else:
                raise ValueError("Can't process description: '{}'".format(literal))
        except ValueError as e:
            print(e)
            return ["Scenario{}".format(i) for i in range(self.total)]


class PresamplesContributions(Contributions):
    mlca: PresamplesMLCA

    def __init__(self, mlca):
        if not isinstance(mlca, PresamplesMLCA):
            raise TypeError("Must pass a PresamplesMLCA object. Passed: {}".format(type(mlca)))
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
