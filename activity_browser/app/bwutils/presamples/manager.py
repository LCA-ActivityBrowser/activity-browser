# -*- coding: utf-8 -*-
from typing import Iterable, List, Optional, Tuple

import numpy as np
from peewee import IntegrityError
import presamples as ps

from ..manager import ParameterManager


class PresamplesParameterManager(ParameterManager):
    """ Used to recalculate brightway parameters without editing the database
    """
    def recalculate(self, values: List[float]) -> np.ndarray:
        data = super().recalculate(values)
        # After recalculating all the exchanges format them according to
        # presamples requirements: samples as a column of floats.
        samples = data.reshape(1, -1).T
        return samples

    def reformat_indices(self) -> np.ndarray:
        """Additional information is required for storing the indices as presamples."""
        result = np.zeros(len(self.indices), dtype=object)
        for i, idx in enumerate(self.indices):
            result[i] = (idx.input, idx.output, idx.input.database_type)
        return result

    def presamples_from_scenarios(self, name: str, scenarios: Iterable[Tuple[str, Iterable]]) -> (str, str):
        """ When given a iterable of multiple parameter scenarios, construct
        a presamples package with all of the recalculated exchange amounts.
        """
        sample_data = [self.recalculate(list(values)) for _, values in scenarios]
        samples = np.concatenate(sample_data, axis=1)
        indices = self.reformat_indices()

        arrays = ps.split_inventory_presamples(samples, indices)
        ps_id, ps_path = ps.create_presamples_package(
            matrix_data=arrays, name=name, seed="sequential"
        )
        return ps_id, ps_path

    @staticmethod
    def store_presamples_as_resource(name: str, path: str, description: str = None) -> Optional[ps.PresampleResource]:
        if not name or not path:
            return
        data = {"name": name, "path": path}
        if description:
            data["description"] = description
        try:
            resource = ps.PresampleResource.create(**data)
        except IntegrityError as e:
            print(e, "\nUpdating with new path.")
            q = (ps.PresampleResource
                 .update({ps.PresampleResource.path: path,
                          ps.PresampleResource.description: description})
                 .where(ps.PresampleResource.name == name)
                 .execute())
            resource = ps.PresampleResource.get(name=name)
        finally:
            return resource
