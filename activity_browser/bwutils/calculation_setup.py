"""Calculation setup helpers (Brightway ``inv`` / ``ia`` lists + scenario inclusion)."""

from __future__ import annotations

from typing import Sequence

import bw2data as bd
import pandas as pd

from activity_browser.bwutils.superstructure.inclusion import (
    MODE_ADDITION,
    MODE_PRODUCT,
    all_included,
    reconcile_included,
)
from activity_browser.bwutils.superstructure.dataframe import scenario_columns

INV_ACTIVE = "inv_active"
IA_ACTIVE = "ia_active"
_ACTIVE = {"inv": INV_ACTIVE, "ia": IA_ACTIVE}

SCENARIO_PATHS = "scenario_paths"
SCENARIO_SHEETS = "scenario_sheets"
SCENARIO_COMBINE = "scenario_combine"
SCENARIO_INCLUDED = "scenario_included"
SCENARIO_AXES = "scenario_axes"


def active_flags(cs: dict, list_key: str) -> list[bool]:
    n = len(cs.get(list_key, []))
    flags = cs.get(_ACTIVE[list_key]) or [True] * n
    flags = list(flags) + [True] * max(0, n - len(flags))
    return [bool(v) for v in flags[:n]]


def ensure_active_lists(cs: dict) -> None:
    cs[INV_ACTIVE] = active_flags(cs, "inv")
    cs[IA_ACTIVE] = active_flags(cs, "ia")


def move_rows(items: list, flags: list[bool], rows: list[int], dest: int) -> None:
    rows = sorted(set(rows))
    if not rows:
        return
    chunk = [(items[i], flags[i]) for i in rows]
    for i in reversed(rows):
        del items[i]
        del flags[i]
    dest = max(0, min(dest, len(items)))
    dest -= sum(1 for i in rows if i < dest)
    for offset, (item, flag) in enumerate(chunk):
        items.insert(dest + offset, item)
        flags.insert(dest + offset, flag)


def _save(cs_name: str, cs: dict) -> None:
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()


def set_active(cs_name: str, list_key: str, row: int, active: bool) -> None:
    cs = bd.calculation_setups[cs_name]
    ensure_active_lists(cs)
    cs[_ACTIVE[list_key]][row] = bool(active)
    _save(cs_name, cs)


def reorder(cs_name: str, list_key: str, rows: list[int], dest: int) -> None:
    cs = bd.calculation_setups[cs_name]
    ensure_active_lists(cs)
    move_rows(cs[list_key], cs[_ACTIVE[list_key]], rows, dest)
    _save(cs_name, cs)


def active_calculation_setup(cs_name: str) -> dict:
    cs = dict(bd.calculation_setups[cs_name])
    ensure_active_lists(cs)
    cs["inv"] = [fu for fu, ok in zip(cs["inv"], cs[INV_ACTIVE]) if ok]
    cs["ia"] = [m for m, ok in zip(cs["ia"], cs[IA_ACTIVE]) if ok]
    return cs


def get_scenario_persistence(cs: dict) -> dict | None:
    """Return scenario persistence fields, or None if the CS has none."""
    paths = cs.get(SCENARIO_PATHS)
    if not paths:
        return None
    return {
        SCENARIO_PATHS: list(paths),
        SCENARIO_SHEETS: list(cs.get(SCENARIO_SHEETS) or [None] * len(paths)),
        SCENARIO_COMBINE: cs.get(SCENARIO_COMBINE, MODE_PRODUCT),
        SCENARIO_INCLUDED: list(cs.get(SCENARIO_INCLUDED) or []),
        SCENARIO_AXES: [list(ax) for ax in (cs.get(SCENARIO_AXES) or [])],
    }


def set_scenario_persistence(
    cs_name: str,
    *,
    paths: Sequence[str],
    combine: str,
    included: Sequence[str],
    axes: Sequence[Sequence[str]],
    sheets: Sequence[int | None] | None = None,
) -> None:
    """Persist absolute scenario paths, combine mode, included set S, and axes."""
    if combine not in (MODE_PRODUCT, MODE_ADDITION):
        raise ValueError(f"Unknown combine mode: {combine!r}")
    cs = bd.calculation_setups[cs_name]
    cs[SCENARIO_PATHS] = [str(p) for p in paths]
    if sheets is None:
        sheets = [None] * len(paths)
    cs[SCENARIO_SHEETS] = list(sheets)
    cs[SCENARIO_COMBINE] = combine
    cs[SCENARIO_INCLUDED] = list(included)
    cs[SCENARIO_AXES] = [list(ax) for ax in axes]
    _save(cs_name, cs)


def clear_scenario_persistence(cs_name: str) -> None:
    cs = bd.calculation_setups[cs_name]
    for key in (
        SCENARIO_PATHS,
        SCENARIO_SHEETS,
        SCENARIO_COMBINE,
        SCENARIO_INCLUDED,
        SCENARIO_AXES,
    ):
        cs.pop(key, None)
    _save(cs_name, cs)


def filter_scenario_dataframe(
    df: pd.DataFrame, included: Sequence[str]
) -> pd.DataFrame:
    """Restrict scenario columns to members of S (preserve dataframe column order)."""
    if df is None or df.empty:
        return df
    included_set = set(included)
    scen = scenario_columns(df)
    cols = [c for c in scen if c in included_set]
    return pd.DataFrame(data=df.loc[:, cols], index=df.index, columns=cols)


def reconcile_scenario_persistence(
    cs: dict, current_axes: Sequence[Sequence[str]], mode: str
):
    """Reconcile saved S with current axes; returns ReconcileResult."""
    from activity_browser.bwutils.superstructure.inclusion import ReconcileResult

    saved = get_scenario_persistence(cs)
    if saved is None:
        return ReconcileResult(all_included(current_axes, mode), mismatched=False)
    return reconcile_included(
        saved[SCENARIO_INCLUDED],
        saved[SCENARIO_AXES],
        current_axes,
        mode,
    )


def functional_unit_key(functional_unit: dict) -> tuple | int:
    """Reference-flow key from a Brightway calculation-setup ``inv`` entry."""
    return next(iter(functional_unit))


def remove_functional_units_from_calculation_setup(database_name: str) -> bool:
    """Remove ``inv`` entries whose reference flow belongs to *database_name*.

    Brightway does not update ``bd.calculation_setups`` when a database is
    deleted. Call this before ``del bd.databases[...]`` so reference-flow keys
    are still resolvable.

    Returns ``True`` if any calculation setup was modified.
    """
    from activity_browser.bwutils.commontasks import refresh_node

    changed_any = False
    for cs_name, cs in bd.calculation_setups.items():
        inv = cs.get("inv", [])
        if not inv:
            continue
        ensure_active_lists(cs)
        kept_inv: list[dict] = []
        kept_flags: list[bool] = []
        for fu, flag in zip(inv, cs[INV_ACTIVE]):
            key = functional_unit_key(fu)
            if isinstance(key, tuple):
                reference_database = key[0]
            else:
                try:
                    reference_database = refresh_node(key)["database"]
                except Exception:
                    reference_database = None
            if reference_database == database_name:
                continue
            kept_inv.append(fu)
            kept_flags.append(flag)
        if len(kept_inv) == len(inv):
            continue
        cs["inv"] = kept_inv
        cs[INV_ACTIVE] = kept_flags
        _save(cs_name, cs)
        changed_any = True
    return changed_any
