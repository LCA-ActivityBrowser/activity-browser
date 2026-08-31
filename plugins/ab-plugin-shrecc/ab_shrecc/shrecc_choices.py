# -*- coding: utf-8 -*-
"""SHRECC choice lists (lazy import with test-friendly fallbacks)."""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

_FALLBACK_TYNDP_SCENARIOS = ("DE", "GA", "NT")
_FALLBACK_TYNDP_CLIMATE_YEARS = (1995, 2008, 2009)
_FALLBACK_PROSPECTIVE_YEARS = frozenset({2030, 2035, 2040, 2050})
_FALLBACK_COUNTRIES = (
    "AT",
    "BE",
    "CH",
    "CZ",
    "DE",
    "DK",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "IE",
    "IT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
)
_FALLBACK_SOURCES = ("auto", "energy_charts", "tyndp")
_FALLBACK_INVENTORY_RESOLUTIONS = ("annual", "monthly")
_FALLBACK_CONSUMPTION_PROFILES = ("flat", "national_demand")
_FALLBACK_ZERO_CONSUMPTION = ("month_hour_average", "raise")
_FALLBACK_IAM = ("remind-eu",)
_FALLBACK_SUGGESTED_YEARS = (
    2015,
    2016,
    2017,
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
    *sorted(_FALLBACK_PROSPECTIVE_YEARS),
)


@lru_cache(maxsize=1)
def _shrecc_modules():
    try:
        from shrecc.energy_charts import ENERGY_CHARTS_COUNTRIES
        from shrecc.mapping import (
            VALID_CONSUMPTION_PROFILES,
            VALID_INVENTORY_RESOLUTIONS,
        )
        from shrecc.pipeline import PROSPECTIVE_YEARS, VALID_SOURCES
        from shrecc.tyndp import TYNDP_CLIMATE_YEARS, TYNDP_SCENARIOS
    except ImportError:
        return None
    return {
        "countries": tuple(ENERGY_CHARTS_COUNTRIES),
        "tyndp_scenarios": tuple(TYNDP_SCENARIOS),
        "climate_years": tuple(TYNDP_CLIMATE_YEARS),
        "prospective_years": frozenset(PROSPECTIVE_YEARS),
        "sources": tuple(sorted(VALID_SOURCES)),
        "inventory_resolutions": tuple(sorted(VALID_INVENTORY_RESOLUTIONS)),
        "consumption_profiles": tuple(sorted(VALID_CONSUMPTION_PROFILES)),
    }


def energy_charts_countries() -> tuple[str, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_COUNTRIES
    return modules["countries"]


def tyndp_scenarios() -> tuple[str, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_TYNDP_SCENARIOS
    return modules["tyndp_scenarios"]


def tyndp_climate_years() -> tuple[int, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_TYNDP_CLIMATE_YEARS
    return modules["climate_years"]


def prospective_years() -> frozenset[int]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_PROSPECTIVE_YEARS
    return modules["prospective_years"]


def valid_sources() -> tuple[str, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_SOURCES
    return modules["sources"]


def inventory_resolutions() -> tuple[str, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_INVENTORY_RESOLUTIONS
    return modules["inventory_resolutions"]


def consumption_profiles() -> tuple[str, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_CONSUMPTION_PROFILES
    return modules["consumption_profiles"]


def zero_consumption_modes() -> tuple[str, ...]:
    return _FALLBACK_ZERO_CONSUMPTION


def iam_choices() -> tuple[str, ...]:
    return _FALLBACK_IAM


def suggested_years() -> tuple[int, ...]:
    modules = _shrecc_modules()
    if modules is None:
        return _FALLBACK_SUGGESTED_YEARS
    prospective = sorted(modules["prospective_years"])
    historical = tuple(year for year in _FALLBACK_SUGGESTED_YEARS if year not in prospective)
    return historical + tuple(prospective)


def is_year_prospective(year: int) -> bool:
    return int(year) in prospective_years()


def source_for_year(year: int, source: str) -> str:
    normalized = str(source).lower()
    if normalized == "auto":
        return "tyndp" if is_year_prospective(year) else "energy_charts"
    return normalized


def needs_tyndp_fields(config: dict) -> bool:
    source = str(config.get("source", "auto")).lower()
    if source == "tyndp":
        return True
    years: Iterable[int] = config.get("years") or []
    if source == "auto":
        return any(is_year_prospective(int(year)) for year in years)
    return False
