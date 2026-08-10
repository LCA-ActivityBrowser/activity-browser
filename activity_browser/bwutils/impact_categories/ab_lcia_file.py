"""AB impact-category file load/export and shared prepared-dataset importer.

``ABLCIAImporter`` links and writes prepared LCIA datasets (AB-shaped
``list[dict]``). AB and bw2io LCIA file loaders both feed it.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Iterable, Sequence

import bw2data as bd
import pandas as pd
import tqdm
from bw2data import Database, Method, config, methods
from bw2io.importers.base_lcia import LCIAImporter
from bw2io.strategies import (
    convert_uncertainty_types_to_integers,
    drop_falsey_uncertainty_fields_but_keep_zeros,
    drop_unspecified_subcategories,
    link_iterable_by_fields,
    set_biosphere_type,
)

from .common import (
    UNCERTAINTY_FIELDS,
    CancelledError,
    ConflictMode,
    ImportStats,
    activity_for_cf_key,
    apply_name_conflicts,
    cell_str,
    cf_amount_and_uncertainty,
    drop_unlinked_exchanges,
    join_tuple_path,
    raise_if_cancelled,
    split_tuple_path,
    uncertainty_from_series,
    unlinked_exchanges,
)

CFS_SHEET = "CFs"
IMPACT_CATEGORIES_SHEET = "Impact categories"
CFS_COLUMNS = ("method", "flow", "amount", *UNCERTAINTY_FIELDS)
IC_COLUMNS = ("method", "unit", "description")
CFS_SUFFIX = ".cfs.csv"
META_SUFFIX = ".metadata.csv"


def _flow_path_for_activity(act) -> str:
    cats = tuple(act.get("categories") or ())
    return join_tuple_path((act.get("name", ""), *cats))


def _ab_csv_directory_and_stem(base: Path) -> tuple[Path, str]:
    name, lower = base.name, base.name.lower()
    for suffix in (CFS_SUFFIX, META_SUFFIX):
        if lower.endswith(suffix):
            return base.parent, name[: -len(suffix)]
    return base.parent, base.name


def methods_to_ab_records(
    method_names: Iterable[tuple],
    *,
    cancel_check=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build CFs and Impact categories dataframes for the given method keys."""
    ic_rows: list[dict] = []
    cf_rows: list[dict] = []
    names = [tuple(name) for name in method_names]
    for name in tqdm.tqdm(names, desc="Reading impact categories", total=len(names)):
        raise_if_cancelled(cancel_check)
        meta = methods.get(name) or {}
        method_path = join_tuple_path(name)
        ic_rows.append(
            {
                "method": method_path,
                "unit": meta.get("unit") or "",
                "description": meta.get("description") or "",
            }
        )
        for key, cf_data in Method(name).load():
            row = {
                "method": method_path,
                "flow": _flow_path_for_activity(activity_for_cf_key(key)),
                **cf_amount_and_uncertainty(cf_data),
            }
            for field in UNCERTAINTY_FIELDS:
                row.setdefault(field, None)
            cf_rows.append(row)
    raise_if_cancelled(cancel_check)
    return (
        pd.DataFrame(cf_rows, columns=list(CFS_COLUMNS)),
        pd.DataFrame(ic_rows, columns=list(IC_COLUMNS)),
    )


def export_methods_ab_xlsx(
    method_names: Sequence[tuple],
    path: str | Path,
    *,
    cancel_check=None,
) -> Path:
    path = Path(path)
    cfs, ics = methods_to_ab_records(method_names, cancel_check=cancel_check)
    raise_if_cancelled(cancel_check)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        cfs.to_excel(writer, sheet_name=CFS_SHEET, index=False)
        ics.to_excel(writer, sheet_name=IMPACT_CATEGORIES_SHEET, index=False)
    return path


def ab_csv_sibling_path(path: str | Path) -> Path | None:
    """Return the expected sibling path for an AB CSV pair member, or None."""
    path = Path(path)
    name, lower = path.name, path.name.lower()
    if lower.endswith(CFS_SUFFIX):
        return path.with_name(name[: -len(CFS_SUFFIX)] + META_SUFFIX)
    if lower.endswith(META_SUFFIX):
        return path.with_name(name[: -len(META_SUFFIX)] + CFS_SUFFIX)
    return None


def resolve_ab_csv_pair(
    path: str | Path,
    *,
    other_path: str | Path | None = None,
) -> tuple[Path, Path]:
    """Return (cfs_path, metadata_path) for an AB CSV import."""
    path = Path(path)
    lower = path.name.lower()
    if lower.endswith(CFS_SUFFIX):
        cfs_path, ic_path = path, Path(other_path) if other_path else ab_csv_sibling_path(path)
    elif lower.endswith(META_SUFFIX):
        ic_path, cfs_path = path, Path(other_path) if other_path else ab_csv_sibling_path(path)
    else:
        raise ValueError("AB CSV import expects a '.cfs.csv' or '.metadata.csv' file")
    if cfs_path is None or ic_path is None:
        raise FileNotFoundError("Matching AB CSV sibling file not found")
    if not cfs_path.is_file():
        raise FileNotFoundError(f"CF file not found: {cfs_path}")
    if not ic_path.is_file():
        raise FileNotFoundError(f"Metadata file not found: {ic_path}")
    return cfs_path, ic_path


def export_methods_ab_csv_pair(
    method_names: Sequence[tuple],
    base_path: str | Path,
    *,
    cancel_check=None,
) -> tuple[Path, Path]:
    """Write AB CSV pair. ``base_path`` is a directory + stem (no required suffix)."""
    directory, stem = _ab_csv_directory_and_stem(Path(base_path))
    cfs_path = directory / f"{stem}{CFS_SUFFIX}"
    ic_path = directory / f"{stem}{META_SUFFIX}"
    cfs, ics = methods_to_ab_records(method_names, cancel_check=cancel_check)
    raise_if_cancelled(cancel_check)
    cfs.to_csv(cfs_path, index=False)
    ics.to_csv(ic_path, index=False)
    return cfs_path, ic_path


def _exchange_from_cf_row(row: pd.Series) -> dict:
    parts = split_tuple_path(row["flow"])
    if not parts:
        raise ValueError("CF row missing flow path")
    return {
        "name": parts[0],
        "categories": tuple(parts[1:]),
        "amount": float(row["amount"]),
        **uncertainty_from_series(row),
    }


def _method_dataset(name: tuple, unit: str, description: str, filename: str, exchanges: list) -> dict:
    return {
        "name": name,
        "unit": unit,
        "description": description,
        "filename": filename,
        "exchanges": exchanges,
    }


def _records_from_frames(cfs: pd.DataFrame, ics: pd.DataFrame, filename: str) -> list[dict]:
    for col in ("method", "flow", "amount"):
        if col not in cfs.columns:
            raise ValueError(f"AB LCIA file missing CF column '{col}'")
    for col in ("method", "unit", "description"):
        if col not in ics.columns:
            raise ValueError(f"AB LCIA file missing Impact categories column '{col}'")

    meta_by_method: dict[tuple, dict[str, str]] = {}
    for _, row in ics.iterrows():
        key = split_tuple_path(row["method"])
        if key:
            meta_by_method[key] = {
                "unit": cell_str(row.get("unit")),
                "description": cell_str(row.get("description")),
            }

    grouped: dict[tuple, list] = {}
    for _, row in cfs.iterrows():
        if pd.isna(row.get("amount")):
            continue
        key = split_tuple_path(row["method"])
        if key:
            grouped.setdefault(key, []).append(_exchange_from_cf_row(row))

    empty = {"unit": "", "description": ""}
    data = []
    for key, exchanges in grouped.items():
        meta = meta_by_method.pop(key, empty)
        data.append(
            _method_dataset(key, meta["unit"], meta["description"], filename, exchanges)
        )
    for key, meta in meta_by_method.items():
        data.append(_method_dataset(key, meta["unit"], meta["description"], filename, []))
    return data


def load_ab_xlsx(path: str | Path) -> list[dict]:
    """Parse an AB impact-category workbook into LCIAImporter-shaped datasets."""
    path = Path(path)
    return _records_from_frames(
        pd.read_excel(path, sheet_name=CFS_SHEET),
        pd.read_excel(path, sheet_name=IMPACT_CATEGORIES_SHEET),
        path.name,
    )


def load_ab_csv_pair(
    path: str | Path,
    *,
    other_path: str | Path | None = None,
) -> list[dict]:
    """Parse an AB CSV sibling pair into LCIAImporter-shaped datasets."""
    cfs_path, ic_path = resolve_ab_csv_pair(path, other_path=other_path)
    return _records_from_frames(
        pd.read_csv(cfs_path, comment="#"),
        pd.read_csv(ic_path, comment="#"),
        cfs_path.name,
    )


def _reformat_cfs_with_uncertainty(exchanges: list[dict]) -> list[tuple]:
    rows = []
    for obj in exchanges:
        if "input" not in obj:
            continue
        data = {"amount": obj["amount"]}
        for field in UNCERTAINTY_FIELDS:
            if field in obj and obj[field] is not None:
                data[field] = obj[field]
        rows.append((obj["input"], data if len(data) > 1 else obj["amount"]))
    return rows


class ABLCIAImporter(LCIAImporter):
    """
    Shared write/link path for prepared LCIA datasets (bw2io ``LCIAImporter``).

    Accepts AB-shaped ``list[dict]`` from AB or bw2io LCIA file loaders.
    Preserves CF uncertainty on write.
    """

    def __init__(self, data: list[dict], biosphere: str | None = None):
        self.applied_strategies = []
        self.filepath = "(ab-lcia)"
        self.biosphere_name = biosphere or config.biosphere
        if self.biosphere_name not in bd.databases:
            raise ValueError(f"Can't find biosphere database {self.biosphere_name}")
        self.data = data
        self.strategies = [
            set_biosphere_type,
            drop_unspecified_subcategories,
            functools.partial(
                link_iterable_by_fields,
                other=Database(self.biosphere_name),
                fields=("name", "categories"),
            ),
            drop_falsey_uncertainty_fields_but_keep_zeros,
            convert_uncertainty_types_to_integers,
        ]

    def _reformat_cfs(self, ds):
        return _reformat_cfs_with_uncertainty(ds)

    def apply_strategies(self, strategies=None, verbose=False, cancel_check=None):
        for strategy in tqdm.tqdm(
            strategies if strategies is not None else self.strategies,
            desc="Applying strategies",
        ):
            raise_if_cancelled(cancel_check)
            self.apply_strategy(strategy, verbose=verbose)
        raise_if_cancelled(cancel_check)

    def write_methods(self, overwrite=False, verbose=True, cancel_check=None):
        num_methods, num_cfs, num_unlinked = self.statistics(False)
        if num_unlinked:
            raise ValueError(
                f"Can't write unlinked methods ({num_unlinked} unlinked cfs)"
            )
        prepared = []
        for ds in tqdm.tqdm(self.data, desc="Preparing impact categories"):
            raise_if_cancelled(cancel_check)
            prepared.append((ds, self._reformat_cfs(ds["exchanges"])))

        raise_if_cancelled(cancel_check)
        written_names: list[tuple] = []
        preexisting = set(methods)
        try:
            for ds, cfs in tqdm.tqdm(prepared, desc="Writing impact categories"):
                raise_if_cancelled(cancel_check)
                name = tuple(ds["name"])
                if name in methods:
                    if not overwrite:
                        raise ValueError(
                            f"Method {name} already exists. Use overwrite=True"
                        )
                    del methods[name]
                method = Method(name)
                method.register(
                    description=ds.get("description") or "",
                    filename=ds.get("filename") or "",
                    unit=ds.get("unit") or "",
                )
                method.write(cfs)
                written_names.append(name)
        except CancelledError:
            for name in written_names:
                if name not in preexisting:
                    methods.pop(name, None)
            raise
        if verbose:
            print(
                f"Wrote {num_methods} LCIA methods with {num_cfs} characterization factors"
            )


def import_ab_methods(
    data: list[dict],
    *,
    biosphere_name: str,
    conflict_mode: ConflictMode = ConflictMode.SKIP,
    prefix: str | None = None,
    renames: dict[tuple, tuple] | None = None,
    drop_unlinked: bool = False,
) -> ImportStats:
    """Link and write prepared method datasets into the current project."""
    prepared = apply_name_conflicts(
        data,
        set(methods),
        mode=conflict_mode,
        prefix=prefix,
        renames=renames,
    )
    skipped = len(data) - len(prepared)
    importer = ABLCIAImporter(prepared, biosphere=biosphere_name)
    importer.apply_strategies()
    unlinked = len(unlinked_exchanges(importer.data))
    if unlinked and not drop_unlinked:
        return ImportStats(written=0, skipped=skipped, unlinked=unlinked)
    if drop_unlinked:
        importer.data = drop_unlinked_exchanges(importer.data)
        unlinked = 0
    importer.write_methods(
        overwrite=conflict_mode == ConflictMode.OVERWRITE, verbose=False
    )
    return ImportStats(written=len(importer.data), skipped=skipped, unlinked=unlinked)
