# -*- coding: utf-8 -*
import abc

import numpy as np
from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase
from stats_arrays import UncertaintyBase, UndefinedUncertainty
from stats_arrays import uncertainty_choices as uc

EMPTY_UNCERTAINTY = {
    "uncertainty type": UndefinedUncertainty.id,
    "loc": np.NaN,
    "scale": np.NaN,
    "shape": np.NaN,
    "minimum": np.NaN,
    "maximum": np.NaN,
    "negative": False,
}


class BaseUncertaintyInterface(abc.ABC):
    __slots__ = ["_data"]
    KEYS = {
        "uncertainty type",
        "loc",
        "scale",
        "shape",
        "minimum",
        "maximum",
        "negative",
        "pedigree",
    }
    data_type = ""

    def __init__(self, unc_obj):
        self._data = unc_obj

    @property
    def data(self):
        return self._data  # pragma: no cover

    @property
    @abc.abstractmethod
    def amount(self) -> float:
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def uncertainty_type(self) -> UncertaintyBase:
        pass  # pragma: no cover

    @property
    @abc.abstractmethod
    def uncertainty(self) -> dict:
        pass  # pragma: no cover


class ExchangeUncertaintyInterface(BaseUncertaintyInterface):
    """Many kinds of exchanges use uncertainty to describe how 'correct' the
    data is which makes up the amount of the exchange.
    """

    _data: ExchangeProxyBase
    data_type = "exchange"

    @property
    def amount(self) -> float:
        return self._data.amount

    @property
    def uncertainty_type(self) -> UncertaintyBase:
        return self._data.uncertainty_type

    @property
    def uncertainty(self) -> dict:
        return self._data.uncertainty


class ParameterUncertaintyInterface(BaseUncertaintyInterface):
    """All levels of parameters can describe their amounts with uncertainty."""

    _data: ParameterBase
    data_type = "parameter"

    @property
    def amount(self) -> float:
        return self._data.amount

    @property
    def uncertainty_type(self) -> UncertaintyBase:
        return uc[self._data.data.get("uncertainty type", 0)]

    @property
    def uncertainty(self) -> dict:
        return {k: self._data.data.get(k) for k in self.KEYS if k in self._data.data}


class CFUncertaintyInterface(BaseUncertaintyInterface):
    """The characterization factors (CFs) of an impact assessment method can also
    contain uncertainty.

    This is however not certain (ha), as the CF is made up out of a flow key
    and either an amount (float) or the uncertainty values + an amount (dict).

    See the ``Method`` and ``ProcessedDataStore`` classes in the bw2data library.
    """

    _data: tuple
    data_type = "cf"

    @property
    def is_uncertain(self) -> bool:
        return isinstance(self._data[1], dict)

    @property
    def amount(self) -> float:
        return self._data[1]["amount"] if self.is_uncertain else self._data[1]

    @property
    def uncertainty_type(self) -> UncertaintyBase:
        if not self.is_uncertain:
            return UndefinedUncertainty
        return uc[self._data[1].get("uncertainty type", 0)]

    @property
    def uncertainty(self) -> dict:
        if not self.is_uncertain:
            return {}
        return {k: self._data[1].get(k) for k in self.KEYS if k in self._data[1]}


def get_uncertainty_interface(data: object) -> BaseUncertaintyInterface:
    if isinstance(data, ExchangeProxyBase):
        return ExchangeUncertaintyInterface(data)
    elif isinstance(data, ParameterBase):
        return ParameterUncertaintyInterface(data)
    elif isinstance(data, tuple):
        return CFUncertaintyInterface(data)
    else:
        raise TypeError(
            "No uncertainty interface exists for object type {}".format(type(data))
        )
