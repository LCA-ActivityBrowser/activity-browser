# -*- coding: utf-8 -*-
"""SHRECC write() orchestration (no Qt)."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator


@dataclass
class WriteTarget:
    year: int
    database_name: str
    will_overwrite: bool


@dataclass
class WriteResult:
    written: dict[int, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def write_targets(
    create_handle: Any,
    existing_database_names: Iterable[str],
) -> list[WriteTarget]:
    existing = set(existing_database_names)
    targets: list[WriteTarget] = []
    for year in create_handle.years:
        name = str(create_handle.database_names[year])
        targets.append(
            WriteTarget(
                year=int(year),
                database_name=name,
                will_overwrite=name in existing,
            )
        )
    return targets


def needs_overwrite_confirm(targets: Iterable[WriteTarget]) -> bool:
    return any(target.will_overwrite for target in targets)


def run_write(create_handle: Any) -> WriteResult:
    """Run ``NewDatabase.write()`` only.

    Call :func:`refresh_written_databases` on the GUI thread after this returns
    so metadata reload does not race SQLite while the write/vacuum still holds
    the database lock.
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


def refresh_written_databases(
    written: dict[int, str],
    after_database_write: Callable[[str], None],
) -> None:
    """Refresh AB metadata for databases that were written (GUI thread)."""
    for name in written.values():
        after_database_write(name)


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
