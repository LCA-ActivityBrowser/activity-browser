# -*- coding: utf-8 -*-
from ast import literal_eval
from typing import List, Union

import brightway2 as bw
import numpy as np
import pandas as pd
import presamples as ps

from ..multilca import MLCA, Contributions


class PresamplesMLCA(MLCA):
    """ Subclass of the `MLCA` class which adds another dimension in the form
     of scenarios / presamples arrays.

    The initial calculation will take use the first presamples array.
    After this, each call to `calculate_scenario` will update the inventory
     matrices and recalculate the results.
    """
    def __init__(self, cs_name: str, ps_name: str):
        self.resource = ps.PresampleResource.get_or_none(name=ps_name)
        if not self.resource:
            raise ValueError("Presamples resource with name '{}' not found.".format(ps_name))
        super().__init__(cs_name)
        data = self.resource.metadata
        self.total = data.get("ncols", 1)
        self._current_index = 0

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
        self.current = steps[-1] + 1  # Walk the steps to the new index

    def _construct_lca(self) -> bw.LCA:
        return bw.LCA(
            demand=self.func_units_dict, method=self.methods[0],
            presamples=[self.resource.path]
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

    @property
    def lca_scores_normalized(self) -> np.ndarray:
        """Normalize LCA scores by impact assessment method.
        """
        return self.lca_scores[:, :, self.current] / self.lca_scores[:, :, self.current].max(axis=0)

    def slice(self, obj: Union[dict, np.ndarray]) -> Union[dict, np.ndarray]:
        """ Return a slice of the given object for the current presample array.
        """
        if isinstance(obj, dict):
            return {k[0]: v for k, v in obj.items() if k[1] == self.current}
        if isinstance(obj, np.ndarray):
            return obj[:, :, self.current]

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
        description = self.resource.description
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
    def __init__(self, mlca):
        if not isinstance(mlca, PresamplesMLCA):
            raise TypeError("Must pass a PresamplesMLCA object. Passed: {}".format(type(mlca)))
        super().__init__(mlca)

    def _build_inventory(self, inventory: dict, indices: dict, columns: list,
                         fields: list) -> pd.DataFrame:
        inventory = self.mlca.slice(inventory)
        return super()._build_inventory(inventory, indices, columns, fields)

    def lca_scores_df(self, normalized: bool = False) -> pd.DataFrame:
        """Returns a metadata-annotated DataFrame of the LCA scores.
        """
        scores = self.mlca.slice(self.mlca.lca_scores) if not normalized else self.mlca.lca_scores_normalized
        return super()._build_lca_scores_df(
            scores, self.mlca.fu_activity_keys, self.mlca.methods, self.act_fields
        )

    def _build_contributions(self, data: np.ndarray, index: int, axis: int) -> np.ndarray:
        data = self.mlca.slice(data)
        return super()._build_contributions(data, index, axis)
