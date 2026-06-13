"""Contributor axis labels for LCA contribution plots."""

from __future__ import annotations

import bw2data as bd
import pandas as pd

from activity_browser.bwutils.commontasks import format_reference_flow_label

REST_ROWS = frozenset({"Rest (+)", "Rest (-)"})
SPECIAL_ROWS = frozenset({"Score", *REST_ROWS})


def is_rest_row(label: str) -> bool:
    return str(label).strip() in REST_ROWS


def contribution_row_labels(df: pd.DataFrame) -> list[str]:
    """Contributor labels using reference-flow formatting when keys are available."""
    if "index" not in df.columns:
        return [str(i).strip() for i in df.index]

    has_keys = "database" in df.columns and "code" in df.columns
    labels: list[str] = []
    for _, row in df.iterrows():
        text = str(row["index"]).strip()
        if text in SPECIAL_ROWS or not has_keys:
            labels.append(text)
            continue
        db, code = row["database"], row["code"]
        if pd.isna(db) or pd.isna(code):
            labels.append(text)
            continue
        try:
            labels.append(format_reference_flow_label(bd.get_activity((db, code))))
        except Exception:
            labels.append(text)
    return labels


def contribution_column_labels(tab, column_names: list) -> list[str]:
    """Category-axis labels; reference flows when comparing impact categories."""
    names = [str(c).strip() for c in column_names]
    if tab is None or not hasattr(tab, "switches"):
        return names
    if tab.switches.currentIndex() != tab.switches.indexes.func:
        return names
    mlca = getattr(tab.parent, "mlca", None)
    if mlca is None:
        return names
    keys = list(mlca.fu_activity_keys)
    if len(keys) != len(names):
        return names
    try:
        return [format_reference_flow_label(bd.get_activity(k)) for k in keys]
    except Exception:
        return names
