"""Shared basename construction for Activity Browser exports."""

from __future__ import annotations

from enum import Enum
from typing import Any


_CONTRIBUTION_TAB_LABELS = {
    "EF contributions": "EF",
    "Process contributions": "process",
    "First Tier contributions": "first_tier",
}


def export_name_slug(value: Any) -> str:
    """Turn a label, enum, or tuple into a short filesystem-safe slug segment."""
    if value is None:
        return ""
    if isinstance(value, Enum):
        text = str(value.value)
    elif isinstance(value, tuple):
        text = "_".join(str(part) for part in value)
    else:
        text = str(value)
    text = (
        text.replace(",", "")
        .replace("'", "")
        .replace("/", "_")
        .replace(" × ", "_x_")
        .replace("×", "_x_")
        .replace(" ", "_")
        .replace("%", "pct")
    )
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def relativity_export_slug(*, relative: bool, total_range: bool = True) -> str:
    """Short slug for relative (_rel) or absolute (_abs) display."""
    del total_range  # retained for call-site compatibility
    return "rel" if relative else "abs"


def lcia_compare_export_slug(mode) -> str:
    """Short slug for LCA-scores compare modes."""
    from activity_browser.bwutils.lcia_overview import LCIACompareMode

    mapping = {
        LCIACompareMode.REFERENCE_FLOWS: "ref_flows",
        LCIACompareMode.FLOWS_X_METHODS: "ref_flows_x_impacts",
        LCIACompareMode.FLOWS_X_SCENARIOS: "ref_flows_x_scenarios",
        LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS: "ref_flows_x_scenarios_x_impacts",
    }
    return mapping.get(mode, export_name_slug(mode))


def contribution_compare_export_slug(switch_index: int, indexes) -> str:
    """Short slug for the active contribution comparison axis."""
    if switch_index == indexes.func:
        return "ref_flows"
    if switch_index == indexes.method:
        return "impacts"
    if switch_index == indexes.scenario:
        return "scenarios"
    return "contributions"


def contribution_tab_slug(label: str) -> str:
    """Short tab label for contribution exports."""
    return _CONTRIBUTION_TAB_LABELS.get(label, export_name_slug(label))


def flip_export_slug(*, flipped: bool) -> str | None:
    """Return flip suffix ``f`` when groups are flipped."""
    return "f" if flipped else None


def activity_export_fields(act) -> list[str]:
    """Product, process, location, and database slug segments for an activity."""
    from activity_browser.bwutils.commontasks import reference_flow_parts

    product, process_name, location, database = reference_flow_parts(act)
    return [
        export_name_slug(part)
        for part in (product, process_name, location, database)
        if part
    ]


def lca_export_basename(*fields) -> str:
    """Join export name parts into a safe default basename.

    Used across LCA Results tabs with the pattern
    ``{cs}_{tab label}_{functional unit}_{method}_{scenario}`` (omit empty parts).
    Tuple fields (e.g. impact categories) are slugged automatically.
    """
    parts = []
    for field in fields:
        if field is None or field == "":
            continue
        if isinstance(field, tuple):
            parts.append(export_name_slug(field))
        elif isinstance(field, Enum):
            parts.append(export_name_slug(field))
        else:
            slug = export_name_slug(field)
            if slug:
                parts.append(slug)
    return "_".join(parts)
