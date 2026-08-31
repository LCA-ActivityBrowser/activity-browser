# -*- coding: utf-8 -*-
"""SHRECC write() orchestration (no Qt)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


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


def run_write(
    create_handle: Any,
    after_database_write: Callable[[str], None],
) -> WriteResult:
    try:
        create_handle.write()
        written = {int(year): str(name) for year, name in create_handle.written_database_names.items()}
        for name in written.values():
            after_database_write(name)
        return WriteResult(written=written)
    except BaseException as exc:
        partial = {
            int(year): str(name)
            for year, name in getattr(create_handle, "written_database_names", {}).items()
        }
        for name in partial.values():
            after_database_write(name)
        return WriteResult(written=partial, error=str(exc))
