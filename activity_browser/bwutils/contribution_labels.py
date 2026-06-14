"""Axis and legend labels for LCA contribution plots."""

from __future__ import annotations

import bw2data as bd
import pandas as pd

from activity_browser.bwutils.commontasks import get_fu_label, get_method_label, unit_of_method

REST_ROWS = frozenset({"Rest (+)", "Rest (-)"})
SPECIAL_ROWS = frozenset({"Score", *REST_ROWS})


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
    biosphere = "categories" in df.columns or (
        has_keys
        and df["database"].dropna().astype(str).str.strip().isin({"biosphere3", "biosphere"}).any()
    )
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
        if biosphere:
            parts = [
                str(row[f]).strip()
                for f in ("name", "categories")
                if f in row.index and pd.notna(row[f]) and str(row[f]).strip()
            ]
            labels.append(" | ".join(parts) if parts else text)
            continue
        try:
            labels.append(get_fu_label(bd.get_activity((db, code))))
        except Exception:
            labels.append(text)
    return labels


def contribution_column_labels(tab, column_keys: list) -> list[str]:
    """Map internal column keys (inv indices or method tuples) to display labels."""
    if tab is None or not hasattr(tab, "switches"):
        return [_fallback_column_label(c) for c in column_keys]

    mlca = getattr(tab.parent, "mlca", None)
    if mlca is None:
        return [_fallback_column_label(c) for c in column_keys]

    mode = tab.switches.currentIndex()
    if mode == tab.switches.indexes.func:
        return [mlca.fu_labels[int(str(c).strip())] for c in column_keys]
    if mode == tab.switches.indexes.method:
        labels = []
        for c in column_keys:
            if isinstance(c, tuple):
                labels.append(mlca.method_labels[mlca.methods.index(c)])
            elif str(c).strip().isdigit():
                labels.append(mlca.method_labels[int(str(c).strip())])
            else:
                labels.append(_fallback_column_label(c))
        return labels
    return [_fallback_column_label(c) for c in column_keys]


def _fallback_column_label(col) -> str:
    if isinstance(col, tuple):
        return get_method_label(col)
    return str(col).strip()
