# -*- coding: utf-8 -*-
"""SHRECC write() orchestration (no Qt)."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator

from .configure_model import preview_database_names


@dataclass
class WriteTarget:
    year: int
    database_name: str
    will_overwrite: bool
    source: str = ""
    background_db: str = ""


@dataclass
class WriteResult:
    written: dict[int, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def resolve_output_database_names(
    *,
    base_name: str,
    years: Iterable[int],
) -> dict[int, str]:
    return preview_database_names(base_name=base_name, years=[int(y) for y in years])


def apply_output_database_names(
    create_handle: Any,
    names_by_year: dict[int, str],
) -> None:
    """Set SHRECC create-handle output names used by ``write()``."""
    updated = dict(getattr(create_handle, "database_names", {}) or {})
    for year, name in names_by_year.items():
        updated[int(year)] = str(name)
    create_handle.database_names = updated


def write_targets(
    create_handle: Any,
    existing_database_names: Iterable[str],
    *,
    output_names: dict[int, str] | None = None,
    summary_rows: Iterable[dict[str, Any]] | None = None,
) -> list[WriteTarget]:
    existing = set(existing_database_names)
    summary_by_year = {
        int(row["year"]): row for row in (summary_rows or []) if "year" in row
    }
    years = [int(year) for year in create_handle.years]
    names = output_names or {
        int(year): str(create_handle.database_names[year]) for year in years
    }
    targets: list[WriteTarget] = []
    for year in years:
        name = str(names.get(year) or create_handle.database_names.get(year) or "")
        row = summary_by_year.get(year) or {}
        targets.append(
            WriteTarget(
                year=year,
                database_name=name,
                will_overwrite=bool(name) and name in existing,
                source=str(row.get("source") or getattr(create_handle, "sources", {}).get(year, "")),
                background_db=str(
                    row.get("background_db")
                    or getattr(create_handle, "background_databases", {}).get(year, "")
                ),
            )
        )
    return targets


def needs_overwrite_confirm(targets: Iterable[WriteTarget]) -> bool:
    return any(target.will_overwrite for target in targets)


def run_write(create_handle: Any) -> WriteResult:
    """Run ``NewDatabase.write()`` only.

    Writes should emit Brightway ``on_database_write`` (e.g. ``signal=True``).
    Host Metadata store reload is deferred until the worker's
    ``safe_bw_connection`` / ``run_blocking_operation`` exits.
    """
    try:
        with _ensure_product_field_on_write():
            create_handle.write()
        written = {
            int(year): str(name)
            for year, name in create_handle.written_database_names.items()
        }
        return WriteResult(written=written)
    except BaseException as exc:
        partial = {
            int(year): str(name)
            for year, name in getattr(
                create_handle, "written_database_names", {}
            ).items()
        }
        return WriteResult(written=partial, error=str(exc))


@contextmanager
def _ensure_product_field_on_write() -> Iterator[None]:
    """SHRECC sets ``reference product`` but not ``product``.

    Brightway's activitydataset ``product`` column then stays null, which
    Activity Browser displays as ``nan`` (NaN is truthy in Python ``or``).
    """
    try:
        from shrecc import database as shrecc_database
    except ImportError:
        yield
        return

    original = shrecc_database.create_activity_dict

    def patched(*args, **kwargs):
        activities = original(*args, **kwargs)
        for act in activities.values():
            product = act.get("product")
            if product is None or (isinstance(product, float) and product != product):
                act["product"] = (
                    act.get("reference product")
                    or act.get("name")
                    or "electricity"
                )
        return activities

    shrecc_database.create_activity_dict = patched
    try:
        yield
    finally:
        shrecc_database.create_activity_dict = original
