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
import math
from pprint import pformat

from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase

VERSION_2 = {
    "reliability": (1.0, 1.54, 1.61, 1.69, 1.69),
    "completeness": (1.0, 1.03, 1.04, 1.08, 1.08),
    "temporal correlation": (1.0, 1.03, 1.1, 1.19, 1.29),
    "geographical correlation": (1.0, 1.04, 1.08, 1.11, 1.11),
    "further technological correlation": (1.0, 1.18, 1.65, 2.08, 2.8),
    "sample size": (1.0, 1.0, 1.0, 1.0, 1.0),
}


class PedigreeMatrix(object):
    __slots__ = ["factors"]
    labels = (
        "reliability",
        "completeness",
        "temporal correlation",
        "geographical correlation",
        "further technological correlation",
        "sample size",
    )

    def __init__(self):
        self.factors = {}

    @classmethod
    def from_numbers(cls, data: tuple) -> "PedigreeMatrix":
        """Takes a tuple of integers and construct a PedigreeMatrix."""
        assert len(data) in (5, 6), "Must provide either 5 or 6 factors"
        if len(data) == 5:
            data = data + (1,)
        matrix = cls()
        for index, factor in enumerate(data):
            matrix.factors[cls.labels[index]] = factor
        return matrix

    @classmethod
    def from_dict(cls, data: dict) -> "PedigreeMatrix":
        return cls.from_numbers(tuple(data.get(k) for k in cls.labels if k in data))

    @classmethod
    def from_bw_object(cls, obj) -> "PedigreeMatrix":
        if isinstance(obj, ExchangeProxyBase):
            return cls.from_dict(obj.get("pedigree", {}))
        elif isinstance(obj, ParameterBase) and "pedigree" in obj.data:
            return cls.from_dict(obj.data.get("pedigree", {}))
        else:
            raise AssertionError("Could not find pedigree in object")

    def calculate(
        self, basic_uncertainty: float = 1.0, as_geometric_sigma: bool = False
    ) -> float:
        """Calculates the sigma or geometric standard deviation from the factors."""
        values = [basic_uncertainty] + self.get_values()
        sigma = math.sqrt(sum([math.log(x) ** 2 for x in values])) / 2
        return sigma if not as_geometric_sigma else math.exp(2 * sigma)

    def get_values(self) -> list:
        assert self.factors, "Must provide Pedigree Matrix factors"
        return [VERSION_2[key][index - 1] for key, index in self.factors.items()]

    def factors_as_tuple(self):
        return tuple(self.factors[k] for k in self.labels if k in self.factors)

    def __repr__(self) -> str:
        return "Empty Pedigree Matrix" if not self.factors else pformat(self.factors)
