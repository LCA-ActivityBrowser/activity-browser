# -*- coding: utf-8 -*-
from ast import literal_eval
from typing import List

import brightway2 as bw
import presamples as ps

from ..multilca import MLCA


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
        idx = next(iter(self.lca.presamples.matrix_indexer))
        self.total = idx.ncols
        self.current = 0

    def _construct_lca(self) -> bw.LCA:
        return bw.LCA(
            demand=self.func_units_dict, method=self.methods[0],
            presamples=[self.resource.path]
        )

    def get_steps_to_index(self, index: int) -> int:
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
            return len(range(index)) + len(range(self.current, self.total))
        else:
            return len(range(self.current, index))

    def calculate_scenario(self, steps: int = 1) -> None:
        """ Update the LCA matrices with the presamples arrays and redo
         the calculations.

        Setting a `steps` value allows us to avoid running all the calculations
         if we only want to look at (for example) the 1st and 5th scenarios.
        """
        # Iterate through the alternate matrices until the correct
        # one is reached
        for _ in range(steps):
            self.lca.presamples.update_matrices(self.lca)
            self.current += 1
            if self.current == self.total:
                self.current = 0
        # Recalculate everything, replacing all of the LCA data
        self._perform_calculations()

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
