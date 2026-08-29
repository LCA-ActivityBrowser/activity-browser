"""LCIA overview matrix slicing, normalization, and tidy data for the landing tab plot."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

import bw2data as bd

from activity_browser.bwutils.commontasks import reference_flow_parts, unit_of_method

if TYPE_CHECKING:
    from activity_browser.bwutils.multilca import MLCA
    from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA


class LCIACompareMode(str, Enum):
    REFERENCE_FLOWS = "reference_flows"
    FLOWS_X_METHODS = "flows_x_methods"
    FLOWS_X_SCENARIOS = "flows_x_scenarios"
    FLOWS_X_SCENARIOS_X_METHODS = "flows_x_scenarios_x_methods"


LCIA_COMPARE_LABELS: dict[LCIACompareMode, str] = {
    LCIACompareMode.REFERENCE_FLOWS: "Reference Flows",
    LCIACompareMode.FLOWS_X_METHODS: "Reference Flows × Impact Categories",
    LCIACompareMode.FLOWS_X_SCENARIOS: "Reference Flows × Scenarios",
    LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS: (
        "Reference Flows × Scenarios × Impact Categories"
    ),
}


def lcia_compare_label(mode: LCIACompareMode) -> str:
    """UI label for an LCIA compare mode."""
    return LCIA_COMPARE_LABELS[mode]


def lcia_compare_mode_from_label(label: str) -> LCIACompareMode:
    """Map combo-box text back to :class:`LCIACompareMode`."""
    for mode, text in LCIA_COMPARE_LABELS.items():
        if text == label:
            return mode
    return LCIACompareMode.REFERENCE_FLOWS


def lcia_compare_labels_for_modes(modes: list[LCIACompareMode]) -> list[str]:
    """Ordered UI labels for the compare modes available in the current setup."""
    return [LCIA_COMPARE_LABELS[mode] for mode in modes]


RELATIVE_Y_LABEL = "% of max |impact|"

# Trailing identity columns on the LCA scores table (plot still uses labels).
RF_TABLE_COLUMNS = ("amount", "unit", "product", "process", "location", "database")
SCORE_TABLE_COLUMNS = ("index", "series", "absolute", "relative", "score unit")


@dataclass
class LCIAOverviewPanel:
    """One grouped bar chart (used for multi-panel compare modes)."""

    title: str
    values: np.ndarray
    absolute_values: np.ndarray
    group_labels: list[str]
    series_labels: list[str]
    group_units: dict[str, str]
    y_label: str


@dataclass
class LCIAOverviewData:
    """Grouped bar chart payload (groups × series), optionally as subplots."""

    values: np.ndarray
    absolute_values: np.ndarray
    group_labels: list[str]
    series_labels: list[str]
    group_units: dict[str, str]
    y_label: str
    normalized: bool
    table_df: pd.DataFrame
    series_units: dict[str, str] = field(default_factory=dict)
    panels: list[LCIAOverviewPanel] = field(default_factory=list)


def lcia_scores_array(mlca: MLCA | SuperstructureMLCA, scenario_index: int = 0) -> np.ndarray:
    scores = mlca.lca_scores
    if scores.ndim == 3:
        return scores[:, :, scenario_index]
    return scores


def normalize_column(column: np.ndarray, *, relative: bool) -> np.ndarray:
    """Normalize a 1-D slice to a percent scale.

    Relative mode divides by ``max(|values|)`` in the slice, e.g.
    ``[-3, 5, 10] → [-30%, 50%, 100%]`` and ``[-11, 5, 10] → [-100%, …]``.
    """
    if not relative:
        return column.astype(float)
    col = column.astype(float)
    denom = float(np.nanmax(np.abs(col)))
    if not denom or np.isnan(denom):
        if np.all(np.isnan(col)) or np.all(col == 0):
            return np.zeros(column.shape, dtype=float)
        return np.full(column.shape, np.nan, dtype=float)
    return 100.0 * col / denom


def normalize_lcia_matrix(scores: np.ndarray, *, relative: bool) -> np.ndarray:
    """Normalize each impact-category column by max(|score|) across reference flows."""
    out = np.zeros_like(scores, dtype=float)
    for col in range(scores.shape[1]):
        out[:, col] = normalize_column(scores[:, col], relative=relative)
    return out


def compare_mode_supports_flip(mode: LCIACompareMode) -> bool:
    return mode in (
        LCIACompareMode.FLOWS_X_METHODS,
        LCIACompareMode.FLOWS_X_SCENARIOS,
        LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS,
    )


def _normalize_grouped_matrix(absolute: np.ndarray, *, relative: bool) -> np.ndarray:
    """Normalize grouped bars: one column → shared scale; multiple series → per group."""
    if not relative:
        return absolute.astype(float)
    values = np.zeros_like(absolute, dtype=float)
    if absolute.shape[1] == 1:
        values[:, 0] = normalize_column(absolute[:, 0], relative=True)
    else:
        for g in range(absolute.shape[0]):
            values[g, :] = normalize_column(absolute[g, :], relative=True)
    return values


def _grouped_matrix(
    absolute: np.ndarray,
    dim0_labels: list[str],
    dim1_labels: list[str],
    *,
    groups_along_dim0: bool,
    relative: bool,
    group_units: dict[str, str],
    y_label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], list[str]]:
    if groups_along_dim0:
        abs_values = absolute.astype(float)
        group_labels = dim0_labels
        series_labels = dim1_labels
    else:
        abs_values = absolute.T.astype(float)
        group_labels = dim1_labels
        series_labels = dim0_labels

    rel_values = _normalize_grouped_matrix(abs_values, relative=True)
    values = rel_values if relative else abs_values
    return values, abs_values, rel_values, group_labels, series_labels


def _reference_flow_table_rows(mlca: MLCA | SuperstructureMLCA) -> list[dict]:
    """One identity row per calculation-setup reference flow (stable FU index)."""
    rows: list[dict] = []
    empty = {col: "" for col in RF_TABLE_COLUMNS}
    for fu in mlca.func_units:
        if not fu:
            rows.append(dict(empty))
            continue
        key = next(iter(fu))
        amount = next(iter(fu.values()))
        product = process = location = unit = database = ""
        try:
            act = bd.get_activity(key)
            product, process, location, database = reference_flow_parts(act)
            unit = str(act.get("unit") or "")
        except Exception:
            if isinstance(key, tuple) and key:
                database = str(key[0])
        rows.append(
            {
                "amount": amount,
                "unit": unit,
                "product": product,
                "process": process,
                "location": location,
                "database": database,
            }
        )
    return rows


def _table_from_matrix(
    abs_values: np.ndarray,
    rel_values: np.ndarray,
    group_labels: list[str],
    series_labels: list[str],
    group_units: dict[str, str],
    *,
    panel: str | None = None,
    series_units: dict[str, str] | None = None,
    fu_rows: list[dict] | None = None,
    fu_on: str = "group",
) -> pd.DataFrame:
    rows = []
    for g_idx, group in enumerate(group_labels):
        for s_idx, series in enumerate(series_labels):
            score_unit = group_units.get(group, "") or (series_units or {}).get(series, "")
            row = {
                "index": group,
                "series": series,
                "absolute": float(abs_values[g_idx, s_idx]),
                "relative": float(rel_values[g_idx, s_idx]),
                "score unit": score_unit,
            }
            if fu_rows:
                fu_idx = g_idx if fu_on == "group" else s_idx
                if 0 <= fu_idx < len(fu_rows):
                    row.update(fu_rows[fu_idx])
            if panel is not None:
                row["impact category"] = panel
            rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    leading = [c for c in SCORE_TABLE_COLUMNS if c in df.columns]
    if "impact category" in df.columns:
        leading.append("impact category")
    trailing = [c for c in RF_TABLE_COLUMNS if c in df.columns]
    rest = [c for c in df.columns if c not in leading and c not in trailing]
    return df.loc[:, leading + rest + trailing]


def _method_group_units(method_labels: list[str], mlca: MLCA) -> dict[str, str]:
    return {label: unit_of_method(m) for label, m in zip(method_labels, mlca.methods)}


def _flows_x_methods_matrix(
    absolute: np.ndarray,
    fu_labels: list[str],
    method_labels: list[str],
    method_units: dict[str, str],
    *,
    relative: bool,
    flip_groups: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str], list[str], dict[str, str], str]:
    """FU × IC matrix; relative scores normalized per impact category."""
    abs_matrix = absolute.astype(float)
    cell_relative = normalize_lcia_matrix(abs_matrix, relative=True)

    if flip_groups:
        abs_values = abs_matrix
        rel_values = cell_relative
        group_labels = fu_labels
        series_labels = method_labels
        group_units = {g: "" for g in fu_labels}
        y_label = RELATIVE_Y_LABEL if relative else "impact"
    else:
        abs_values = abs_matrix.T
        rel_values = cell_relative.T
        group_labels = method_labels
        series_labels = fu_labels
        group_units = method_units
        y_label = RELATIVE_Y_LABEL if relative else "impact"

    values = rel_values if relative else abs_values
    return values, abs_values, rel_values, group_labels, series_labels, group_units, y_label


def build_lcia_overview(
    mlca: MLCA | SuperstructureMLCA,
    contributions,
    *,
    compare: LCIACompareMode,
    relative: bool,
    scenario_index: int = 0,
    method_index: int = 0,
    flip_groups: bool = False,
) -> LCIAOverviewData:
    """Build grouped-bar data for the LCIA landing tab."""
    fu_labels = list(mlca.fu_labels.values())
    method_labels = list(mlca.method_labels.values())
    method_units = _method_group_units(method_labels, mlca)
    fu_rows = _reference_flow_table_rows(mlca)

    if compare == LCIACompareMode.REFERENCE_FLOWS:
        absolute = lcia_scores_array(mlca, scenario_index)[:, [method_index]]
        unit = unit_of_method(mlca.methods[method_index])
        group_units = {g: unit for g in fu_labels}
        y_label = unit if not relative else RELATIVE_Y_LABEL
        values, abs_values, rel_values, group_labels, series_labels = _grouped_matrix(
            absolute,
            fu_labels,
            [method_labels[method_index]],
            groups_along_dim0=True,
            relative=relative,
            group_units=group_units,
            y_label=y_label,
        )

    elif compare == LCIACompareMode.FLOWS_X_METHODS:
        absolute = lcia_scores_array(mlca, scenario_index)
        (
            values,
            abs_values,
            rel_values,
            group_labels,
            series_labels,
            group_units,
            y_label,
        ) = _flows_x_methods_matrix(
            absolute,
            fu_labels,
            method_labels,
            method_units,
            relative=relative,
            flip_groups=flip_groups,
        )

    elif compare == LCIACompareMode.FLOWS_X_SCENARIOS:
        if not hasattr(mlca, "scenario_names"):
            raise ValueError("Scenario comparison requires scenario LCA results")
        scenario_labels = list(mlca.scenario_names)
        absolute = mlca.lca_scores[:, method_index, :]
        unit = unit_of_method(mlca.methods[method_index])
        group_units = (
            {g: unit for g in fu_labels}
            if not flip_groups
            else {g: unit for g in scenario_labels}
        )
        y_label = unit if not relative else RELATIVE_Y_LABEL
        values, abs_values, rel_values, group_labels, series_labels = _grouped_matrix(
            absolute,
            fu_labels,
            scenario_labels,
            groups_along_dim0=not flip_groups,
            relative=relative,
            group_units=group_units,
            y_label=y_label,
        )

    elif compare == LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS:
        if not hasattr(mlca, "scenario_names"):
            raise ValueError("Scenario comparison requires scenario LCA results")
        scenario_labels = list(mlca.scenario_names)
        panels: list[LCIAOverviewPanel] = []
        table_parts: list[pd.DataFrame] = []
        for m_idx, method_label in enumerate(method_labels):
            absolute = mlca.lca_scores[:, m_idx, :]
            unit = unit_of_method(mlca.methods[m_idx])
            group_units = (
                {g: unit for g in fu_labels}
                if not flip_groups
                else {g: unit for g in scenario_labels}
            )
            y_label = unit if not relative else RELATIVE_Y_LABEL
            p_values, p_abs, p_rel, p_groups, p_series = _grouped_matrix(
                absolute,
                fu_labels,
                scenario_labels,
                groups_along_dim0=not flip_groups,
                relative=relative,
                group_units=group_units,
                y_label=y_label,
            )
            panels.append(
                LCIAOverviewPanel(
                    title=method_label,
                    values=p_values,
                    absolute_values=p_abs,
                    group_labels=p_groups,
                    series_labels=p_series,
                    group_units=group_units,
                    y_label=y_label,
                )
            )
            table_parts.append(
                _table_from_matrix(
                    p_abs,
                    p_rel,
                    p_groups,
                    p_series,
                    group_units,
                    panel=method_label,
                    fu_rows=fu_rows,
                    fu_on="group" if not flip_groups else "series",
                )
            )
        return LCIAOverviewData(
            values=np.array([]),
            absolute_values=np.array([]),
            group_labels=[],
            series_labels=[],
            group_units={},
            y_label=panels[0].y_label if panels else "",
            normalized=relative,
            table_df=pd.concat(table_parts, ignore_index=True) if table_parts else pd.DataFrame(),
            panels=panels,
        )

    else:
        raise ValueError(f"Unknown compare mode: {compare}")

    if compare == LCIACompareMode.REFERENCE_FLOWS:
        fu_on = "group"
    elif compare == LCIACompareMode.FLOWS_X_METHODS:
        fu_on = "group" if flip_groups else "series"
    else:
        fu_on = "group" if not flip_groups else "series"

    series_units = (
        method_units
        if compare == LCIACompareMode.FLOWS_X_METHODS and flip_groups
        else None
    )
    table_df = _table_from_matrix(
        abs_values,
        rel_values,
        group_labels,
        series_labels,
        group_units,
        series_units=series_units,
        fu_rows=fu_rows,
        fu_on=fu_on,
    )

    return LCIAOverviewData(
        values=values,
        absolute_values=abs_values,
        group_labels=group_labels,
        series_labels=series_labels,
        group_units=group_units,
        y_label=y_label,
        normalized=relative,
        table_df=table_df,
        series_units=series_units or {},
    )


def available_compare_modes(mlca: MLCA, has_scenarios: bool) -> list[LCIACompareMode]:
    n_fu = len(mlca.func_units)
    n_m = len(mlca.methods)
    n_scen = len(getattr(mlca, "scenario_names", []) or [])
    modes: list[LCIACompareMode] = []
    if n_fu > 0 and n_m > 0:
        modes.append(LCIACompareMode.REFERENCE_FLOWS)
    if n_fu > 0 and n_m > 1:
        modes.append(LCIACompareMode.FLOWS_X_METHODS)
    elif n_fu > 1 and n_m == 1:
        modes.append(LCIACompareMode.FLOWS_X_METHODS)
    if has_scenarios and n_fu > 0 and n_m > 0 and n_scen > 1:
        modes.append(LCIACompareMode.FLOWS_X_SCENARIOS)
    if has_scenarios and n_fu > 0 and n_m > 0 and n_scen > 0:
        modes.append(LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS)
    return modes
