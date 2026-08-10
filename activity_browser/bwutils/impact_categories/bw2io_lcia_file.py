"""bw2io impact-category file load/export (CF table + AB metadata helpers)."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import bw2data as bd
import pandas as pd
import tqdm

from .common import (
    UNCERTAINTY_FIELDS,
    activity_for_cf_key,
    cell_str,
    cf_amount_and_uncertainty,
    join_tuple_path,
    raise_if_cancelled,
    split_tuple_path,
    uncertainty_from_series,
)

BW2IO_CF_COLUMNS = ("name", "categories", "amount", *UNCERTAINTY_FIELDS)
BW2IO_META_COLUMNS = ("filename", "method", "unit", "description")
_FORBIDDEN_FILENAME_CHARS = '<>:"/\\|?*'


def method_name_to_filename_stem(name: tuple) -> str:
    """
    Build a cross-platform filename stem from a Brightway method key.

    Tuple parts are joined with ``__`` (``::`` is illegal on Windows). Remaining
    forbidden characters are replaced with ``-``.
    """
    parts: list[str] = []
    for part in name:
        text = str(part).strip()
        for ch in _FORBIDDEN_FILENAME_CHARS:
            text = text.replace(ch, "-")
        text = "".join(c for c in text if ord(c) >= 32).rstrip(" .")
        parts.append(text or "part")
    stem = "__".join(parts) if parts else "method"
    return (stem[:200].rstrip(" .") if len(stem) > 200 else stem) or "method"


def _method_meta(name: tuple, *, filename: str = "") -> dict[str, str]:
    meta = bd.methods.get(name) or {}
    return {
        "filename": filename,
        "method": join_tuple_path(name),
        "unit": meta.get("unit") or "",
        "description": meta.get("description") or "",
    }


def _cf_frame_for_method(name: tuple) -> pd.DataFrame:
    rows = []
    for key, cf_data in bd.Method(name).load():
        act = activity_for_cf_key(key)
        cats = tuple(act.get("categories") or ())
        row = {
            "name": act.get("name", ""),
            "categories": join_tuple_path(cats) if cats else "",
            **cf_amount_and_uncertainty(cf_data),
        }
        for field in UNCERTAINTY_FIELDS:
            row.setdefault(field, None)
        rows.append(row)
    return pd.DataFrame(rows, columns=list(BW2IO_CF_COLUMNS))


def export_method_bw2io_xlsx(name: tuple, path: str | Path) -> Path:
    path = Path(path)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        _cf_frame_for_method(name).to_excel(writer, sheet_name="CFs", index=False)
        pd.DataFrame(
            [_method_meta(name, filename=path.name)],
            columns=list(BW2IO_META_COLUMNS),
        ).to_excel(writer, sheet_name="metadata", index=False)
    return path


def export_methods_bw2io_csv_batch(
    method_names: Sequence[tuple],
    directory: str | Path,
    *,
    metadata_name: str = "metadata.csv",
    cancel_check=None,
) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    meta_rows = []
    for name in tqdm.tqdm(method_names, desc="Exporting bw2io CSV"):
        raise_if_cancelled(cancel_check)
        cf_name = f"{method_name_to_filename_stem(name)}.csv"
        cf_path = directory / cf_name
        _cf_frame_for_method(name).to_csv(cf_path, index=False)
        written.append(cf_path)
        meta_rows.append(_method_meta(name, filename=cf_name))
    raise_if_cancelled(cancel_check)
    meta_path = directory / metadata_name
    pd.DataFrame(meta_rows, columns=list(BW2IO_META_COLUMNS)).to_csv(
        meta_path, index=False
    )
    written.append(meta_path)
    return written


def _row_to_meta(row: pd.Series) -> dict[str, str]:
    return {key: cell_str(row.get(key)) for key in BW2IO_META_COLUMNS}


def read_bw2io_metadata_xlsx(path: str | Path) -> dict[str, str] | None:
    try:
        meta = pd.read_excel(path, sheet_name="metadata")
    except ValueError:
        return None
    return None if meta.empty else _row_to_meta(meta.iloc[0])


def read_bw2io_metadata_csv(
    metadata_path: str | Path,
    *,
    cf_filename: str | None = None,
) -> dict[str, str] | None:
    """
    Prefill metadata for a CF CSV.

    Match ``filename`` to ``cf_filename`` when that column exists; if there is
    exactly one row, use it; otherwise return ``None``.
    """
    path = Path(metadata_path)
    if not path.is_file():
        return None
    meta = pd.read_csv(path, comment="#")
    if meta.empty:
        return None
    if cf_filename and "filename" in meta.columns:
        match = meta[meta["filename"].astype(str) == str(cf_filename)]
        if len(match) >= 1:
            return _row_to_meta(match.iloc[0])
        return None
    return _row_to_meta(meta.iloc[0]) if len(meta) == 1 else None


def load_bw2io_lcia_file(
    path: str | Path,
    *,
    name: tuple,
    unit: str,
    description: str,
) -> list[dict]:
    """Parse one bw2io CF table into ABLCIAImporter-shaped data (first sheet only for xlsx)."""
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        cfs = pd.read_excel(path, sheet_name=0)
    else:
        cfs = pd.read_csv(path, comment="#")
    if "name" not in cfs.columns or "amount" not in cfs.columns:
        raise ValueError("bw2io LCIA file must include 'name' and 'amount' columns")

    exchanges = []
    for _, row in cfs.iterrows():
        if pd.isna(row.get("amount")):
            continue
        exchanges.append(
            {
                "name": str(row["name"]),
                "categories": split_tuple_path(cell_str(row.get("categories"))),
                "amount": float(row["amount"]),
                **uncertainty_from_series(row),
            }
        )
    return [
        {
            "name": tuple(name),
            "unit": unit or "",
            "description": description or "",
            "filename": path.name,
            "exchanges": exchanges,
        }
    ]
