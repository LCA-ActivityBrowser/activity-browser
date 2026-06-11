# -*- coding: utf-8 -*-
"""
Uncertainty helpers for Activity Browser.

Two roles:

1. **UI interfaces** — wrap exchanges, parameters, and CFs for the uncertainty
   editor dialog (``ExchangeUncertaintyInterface``, etc.).

2. **GSA / reporting** — format stats_arrays data using the same field names and
   labels as ``ui/dialogs/uncertainty_dialog.py``:

   - ``standard_uncertainty_fields`` — active stats_arrays keys per distribution type
   - ``uncertainty_type_name`` — distribution name (e.g. ``Uniform``)
   - ``uncertainty_parameters_summary`` — parameter summary (e.g.
     ``Mode: 5.0; Minimum: 0.0; Maximum: 10.0``)
   - ``uncertainty_cell_summary`` — combined table cell (``Uniform; Minimum: 0; Maximum: 1``)
"""
from __future__ import annotations

import abc

import numpy as np
import stats_arrays as sa
from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase
from stats_arrays import UncertaintyBase, UndefinedUncertainty
from stats_arrays import uncertainty_choices as uc

# Cleared uncertainty state for remove-uncertainty actions and dialog defaults.
EMPTY_UNCERTAINTY = {
    "uncertainty type": UndefinedUncertainty.id,
    "loc": np.NaN,
    "scale": np.NaN,
    "shape": np.NaN,
    "minimum": np.NaN,
    "maximum": np.NaN,
    "negative": False,
}


def uncertainty_type_id(source) -> int:
    """Return stats_arrays uncertainty type id from a dict, exchange proxy, or int."""
    if isinstance(source, int):
        return source
    if not hasattr(source, "get"):
        return 0
    try:
        return int(source.get("uncertainty type", source.get("uncertainty_type", 0)) or 0)
    except (TypeError, ValueError):
        return 0


def uncertainty_type_name(source) -> str:
    """Distribution label for GSA (``Uniform``, ``Triangular``, …)."""
    ut = source if isinstance(source, int) else uncertainty_type_id(source)
    if not ut and not isinstance(source, int):
        return ""
    try:
        description = uc[ut].description
    except KeyError:
        return str(ut)
    if description.endswith(" uncertainty"):
        return description[: -len(" uncertainty")]
    return description


def standard_uncertainty_fields(ut_id: int) -> list[str]:
    """Active stats_arrays keys per type (shared with ``UncertaintyDialog``)."""
    if ut_id in (sa.LognormalUncertainty.id, sa.NormalUncertainty.id):
        return ["loc", "scale"]
    if ut_id in (sa.UniformUncertainty.id, sa.DiscreteUniform.id):
        return ["minimum", "maximum"]
    if ut_id == sa.TriangularUncertainty.id:
        return ["loc", "minimum", "maximum"]
    if ut_id == sa.BernoulliUncertainty.id:
        return ["loc"]
    if ut_id in (sa.WeibullUncertainty.id, sa.GammaUncertainty.id, sa.StudentsTUncertainty.id):
        return ["loc", "scale", "shape"]
    if ut_id == sa.BetaUncertainty.id:
        return ["loc", "shape", "minimum", "maximum"]
    if ut_id == sa.GeneralizedExtremeValueUncertainty.id:
        return ["loc", "scale"]
    return []


def uncertainty_field_name(ut_id: int, field_key: str) -> str:
    """Dialog caption for a stats_arrays field (public for tests)."""
    if field_key == "negative":
        return "Negative"
    if field_key == "loc":
        return {
            sa.BernoulliUncertainty.id: "Probability (0 ≤ p ≤ 1)",
            sa.LognormalUncertainty.id: "Loc (ln(mean))",
            sa.TriangularUncertainty.id: "Mode",
            sa.BetaUncertainty.id: "Alpha (α)",
        }.get(ut_id, "Loc / offset" if ut_id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id) else "Mean / location")
    if field_key == "scale":
        return {
            sa.GammaUncertainty.id: "Scale (θ)",
            sa.WeibullUncertainty.id: "Scale (λ)",
        }.get(
            ut_id,
            "Scale (σ)"
            if ut_id
            in (
                sa.NormalUncertainty.id,
                sa.LognormalUncertainty.id,
                sa.StudentsTUncertainty.id,
                sa.GeneralizedExtremeValueUncertainty.id,
            )
            else "Sigma/scale",
        )
    if field_key == "shape":
        return {
            sa.BetaUncertainty.id: "Beta (β)",
            sa.StudentsTUncertainty.id: "Degrees of freedom (ν)",
        }.get(
            ut_id,
            "Shape (k)" if ut_id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id) else "Shape",
        )
    if field_key == "minimum":
        return "Minimum (inclusive)" if ut_id == sa.DiscreteUniform.id else "Minimum"
    if field_key == "maximum":
        return "Maximum (exclusive)" if ut_id == sa.DiscreteUniform.id else "Maximum"
    return field_key


def _raw_uncertainty_values(source) -> dict:
    """Stats_arrays value fields for ``uncertainty_parameters_summary`` (not pedigree / type)."""
    value_keys = [k for k in EMPTY_UNCERTAINTY if k != "uncertainty type"]
    if hasattr(source, "uncertainty"):
        merged = dict(source.uncertainty)
        for key in value_keys:
            if key in source:
                merged[key] = source.get(key)
    elif isinstance(source, dict):
        merged = source
    else:
        merged = {}
    return {key: merged.get(key, EMPTY_UNCERTAINTY[key]) for key in value_keys}


def uncertainty_parameters_summary(source) -> str:
    """Semicolon-separated uncertainty parameters, using UncertaintyDialog labels."""
    ut_id = uncertainty_type_id(source)
    raw = _raw_uncertainty_values(source)
    parts = []
    for field in standard_uncertainty_fields(ut_id):
        value = raw.get(field, np.nan)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue
        parts.append(f"{uncertainty_field_name(ut_id, field)}: {value}")
    if ut_id in (sa.LognormalUncertainty.id, sa.GammaUncertainty.id, sa.WeibullUncertainty.id):
        parts.append(f"Negative: {bool(raw.get('negative', False))}")
    return "; ".join(parts)


def uncertainty_cell_summary(source) -> str:
    """Single-table-cell text: distribution type and parameters (``Type; param: val; …``)."""
    type_name = uncertainty_type_name(source)
    params = uncertainty_parameters_summary(source)
    if type_name and params:
        return f"{type_name}; {params}"
    return type_name or params


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
    if isinstance(data, ParameterBase):
        return ParameterUncertaintyInterface(data)
    if isinstance(data, tuple):
        return CFUncertaintyInterface(data)
    raise TypeError(f"No uncertainty interface exists for object type {type(data)}")
