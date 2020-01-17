# -*- coding: utf-8 -*
"""
Code in `pedigree.py` is taken wholesale from the https://bitbucket.org/cmutel/pedigree-matrix/src repository,
which is published by Chris Mutel under an MIT license (2012).

FUTURE WORK?
'The application of the pedigree approach to the distributions foreseen in ecoinvent v3'
(doi: 10.1007/s11367-014-0759-5) reveals the formulas used to convert the calculated sigma
(+ geometric standard deviation) into the coefficient of variation ('CV').
In turn, this CV can then be used to generate required values for a number of other uncertainty distributions.

Any additions made should improve the transition of the calculated sigma (or Geometric Standard Deviation/GSD)
smoothly into the related uncertainty distributions.
"""
from collections import namedtuple
import math
from pprint import pformat

import numpy as np
from stats_arrays import uncertainty_choices as uc


VERSION_2 = {
    "reliability": (1., 1.54, 1.61, 1.69, 1.69),
    "completeness": (1., 1.03, 1.04, 1.08, 1.08),
    "temporal correlation": (1., 1.03, 1.1, 1.19, 1.29),
    "geographical correlation": (1., 1.04, 1.08, 1.11, 1.11),
    "further technological correlation": (1., 1.18, 1.65, 2.08, 2.8),
    "sample size": (1., 1., 1., 1., 1.)
}


class PedigreeMatrix(object):
    __slots__ = ["factors"]
    labels = (
        "reliability",
        "completeness",
        "temporal correlation",
        "geographical correlation",
        "further technological correlation",
        "sample size"
    )

    def __init__(self):
        self.factors = {}

    @classmethod
    def from_numbers(cls, data: tuple) -> 'PedigreeMatrix':
        """Takes a tuple of integers and construct a PedigreeMatrix.
        """
        assert len(data) in (5, 6), "Must provide either 5 or 6 factors"
        if len(data) == 5:
            data = data + (1,)
        matrix = cls()
        for index, factor in enumerate(data):
            matrix.factors[cls.labels[index]] = factor
        return matrix

    def calculate(self, basic_uncertainty: float = 1.,
                  as_geometric_sigma: bool = False) -> float:
        """ Calculates the sigma or geometric standard deviation from the factors.
        """
        values = [basic_uncertainty] + self.get_values()
        sigma = math.sqrt(sum([math.log(x) ** 2 for x in values])) / 2
        return sigma if not as_geometric_sigma else math.exp(2 * sigma)

    def get_values(self) -> list:
        assert self.factors, "Must provide Pedigree Matrix factors"
        return [VERSION_2[key][index - 1] for key, index in self.factors.items()]

    def __repr__(self) -> str:
        return "Empty Pedigree Matrix" if not self.factors else pformat(self.factors)


UncertainValues = namedtuple("values", ("loc", "scale", "shape", "min", "max"))


class DistributionGenerator(object):
    """Generator class that is mostly here to have a central place to store
    logic on which values are used in which distributions.

    TODO: finish this at a later date.
    """
    @staticmethod
    def generate_distribution(data: UncertainValues, dist_id: int, size: int = 1000) -> np.ndarray:
        assert dist_id in uc.id_dict
        if dist_id == 2:
            return DistributionGenerator._log_normal(data, size)
        elif dist_id == 3:
            return DistributionGenerator._normal(data, size)

    @staticmethod
    def _log_normal(data: UncertainValues, size: int) -> np.ndarray:
        assert not any(np.isnan([data.loc, data.scale]))
        return np.random.lognormal(mean=data.loc, sigma=data.scale, size=size)

    @staticmethod
    def _normal(data: UncertainValues, size: int) -> np.ndarray:
        assert not any(np.isnan([data.loc, data.scale]))
        return np.random.normal(loc=data.loc, scale=data.scale, size=size)

    @staticmethod
    def _uniform(data: UncertainValues, size: int) -> np.ndarray:
        assert not any(np.isnan([data.min, data.max]))
        return np.random.uniform(low=data.min, high=data.max, size=size)

    @staticmethod
    def _triangular(data: UncertainValues, size: int) -> np.ndarray:
        pass

