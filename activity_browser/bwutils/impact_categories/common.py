"""Shared helpers for impact-category (LCIA) file interchange."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

import bw2data as bd
import pandas as pd

from activity_browser.bwutils.uncertainty import UNCERTAINTY_FIELDS


class ConflictMode(str, Enum):
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME_PREFIX = "rename_prefix"


@dataclass
class ImportStats:
    written: int = 0
    skipped: int = 0
    unlinked: int = 0


class CancelledError(Exception):
    """Raised when the user cancels a long-running LCIA file job."""


def raise_if_cancelled(check) -> None:
    if check and check():
        raise CancelledError()


def join_tuple_path(parts: Sequence[Any]) -> str:
    return "::".join(str(p) for p in parts)


def split_tuple_path(value: str | None) -> tuple[str, ...]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ()
    text = str(value).strip()
    return tuple(p for p in text.split("::") if p) if text else ()


def cell_str(value: Any) -> str:
    """Coerce a spreadsheet cell to ``str``; blank for missing/NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


def apply_name_conflicts(
    data: list[dict],
    existing: set[tuple],
    *,
    mode: ConflictMode,
    prefix: str | None = None,
    renames: dict[tuple, tuple] | None = None,
) -> list[dict]:
    """Return a new method list after applying conflict policy (pure transform)."""
    renames = renames or {}
    result: list[dict] = []
    for ds in data:
        original = tuple(ds["name"])
        name = tuple(renames.get(original, original))
        if name != original:
            ds = {**ds, "name": name}
        if name not in existing:
            result.append(ds)
        elif mode == ConflictMode.SKIP:
            continue
        elif mode == ConflictMode.OVERWRITE:
            result.append(ds)
        elif mode == ConflictMode.RENAME_PREFIX:
            if not prefix:
                raise ValueError("prefix is required for RENAME_PREFIX")
            result.append({**ds, "name": (prefix, *name)})
        else:
            raise ValueError(f"Unknown conflict mode: {mode}")
    return result


def cf_amount_and_uncertainty(cf_data: Any) -> dict[str, Any]:
    if not isinstance(cf_data, dict):
        return {"amount": float(cf_data)}
    row = {"amount": float(cf_data.get("amount", 0))}
    for field in UNCERTAINTY_FIELDS:
        if field in cf_data and cf_data[field] is not None:
            row[field] = cf_data[field]
    return row


def uncertainty_from_series(row: Mapping[str, Any]) -> dict[str, Any]:
    """Typed uncertainty fields from a spreadsheet row (skip missing/NaN)."""
    out: dict[str, Any] = {}
    for field in UNCERTAINTY_FIELDS:
        if field not in row:
            continue
        val = row[field]
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        if field == "uncertainty type":
            out[field] = int(val)
        elif field == "negative":
            out[field] = bool(val)
        else:
            out[field] = float(val)
    return out


def activity_for_cf_key(key: Any):
    try:
        return bd.get_activity(key)
    except Exception:
        return bd.get_node(id=key)


def unlinked_exchanges(data: list[dict]) -> list[dict]:
    return [
        {"method": ds["name"], **exc}
        for ds in data
        for exc in ds.get("exchanges", [])
        if "input" not in exc
    ]


def exchange_link_counts(data: list[dict]) -> tuple[int, int]:
    """Return ``(linked_cf_count, unlinked_cf_count)`` after strategies."""
    total = sum(len(ds.get("exchanges", [])) for ds in data)
    unlinked = len(unlinked_exchanges(data))
    return total - unlinked, unlinked


def drop_unlinked_exchanges(data: list[dict]) -> list[dict]:
    return [
        {**ds, "exchanges": [e for e in ds.get("exchanges", []) if "input" in e]}
        for ds in data
    ]
