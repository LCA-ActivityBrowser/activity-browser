"""Axis and legend labels for LCA contribution plots."""

from __future__ import annotations

import pandas as pd

from activity_browser.bwutils.commontasks import (
    exchange_part_label,
    get_fu_label,
    get_method_label,
    is_node_biosphere,
    refresh_node,
    unit_of_method,
)
from activity_browser.bwutils.multilca import setup_index

REST_ROWS = frozenset({"Rest (+)", "Rest (-)"})
SPECIAL_ROWS = frozenset({"Score", *REST_ROWS})
_COMPARE_LABELS = {
    "fu": "fu_labels",
    "method": "method_labels",
    "scenario": "scenario_labels",
}


def contribution_axis_unit(
    method: tuple | None, *, relative: bool = False, total_range: bool = True
) -> str:
    if relative:
        return "% of range" if total_range else "% of score"
    if method:
        return unit_of_method(method)
    return "units of each impact category"


def is_rest_row(label: str) -> bool:
    return str(label).strip() in REST_ROWS


def contribution_row_labels(df: pd.DataFrame) -> list[str]:
    """Contributor labels for process or elementary-flow rows."""
    has_keys = "database" in df.columns and "code" in df.columns
    labels: list[str] = []
    for _, row in df.iterrows():
        text = str(row["index"]).strip() if "index" in df.columns else ""
        if text in SPECIAL_ROWS or (has_keys and str(row.get("database", "")).strip() in SPECIAL_ROWS):
            labels.append(text or str(row.get("database", "")).strip())
            continue
        if not has_keys:
            labels.append(text or str(row.name).strip())
            continue
        db, code = row["database"], row["code"]
        if pd.isna(db) or pd.isna(code):
            labels.append(text)
            continue
        try:
            node = refresh_node((db, code))
            if is_node_biosphere(node):
                labels.append(exchange_part_label(node))
            else:
                labels.append(get_fu_label(node))
        except Exception:
            labels.append(text)
    return labels


def contribution_column_labels(tab, column_keys: list) -> list[str]:
    """Map setup indices (0, 1, …) to MLCA display labels."""
    if tab is None or not hasattr(tab, "switches"):
        return [_fallback_column_label(c) for c in column_keys]

    mlca = getattr(tab.parent, "mlca", None)
    if mlca is None:
        return [_fallback_column_label(c) for c in column_keys]

    mode = tab.switches.currentIndex()
    if mode == tab.switches.indexes.func:
        compare = "fu"
    elif mode == tab.switches.indexes.method:
        compare = "method"
    elif mode == tab.switches.indexes.scenario:
        compare = "scenario"
    else:
        return [_fallback_column_label(c) for c in column_keys]

    label_dict = getattr(mlca, _COMPARE_LABELS[compare], {}) or {}
    return [
        label_dict.get(setup_index(col), str(col)) if setup_index(col) is not None else str(col)
        for col in column_keys
    ]


def _fallback_column_label(col) -> str:
    if isinstance(col, tuple):
        return get_method_label(col)
    return str(col).strip()
