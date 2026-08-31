# -*- coding: utf-8 -*-
"""SHRECC create() orchestration and inspect artifact building (no Qt)."""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Callable

_PREVIEW_ROW_LIMIT = 100


@dataclass
class CreateResult:
    artifacts: dict[str, Any]
    log_lines: list[str]


def run_create(
    kwargs: dict[str, Any],
    *,
    new_database_factory: Callable[..., Any] | None = None,
) -> tuple[Any, CreateResult]:
    factory = new_database_factory or _default_new_database
    ndb = factory(**kwargs)
    captured: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ndb.create()
        captured = [str(record.message) for record in caught]
    artifacts = build_inspect_artifacts(ndb, warnings=captured)
    log_lines = list(artifacts.get("log") or []) + captured
    return ndb, CreateResult(artifacts=artifacts, log_lines=log_lines)


def build_inspect_artifacts(ndb: Any, *, warnings: list[str]) -> dict[str, Any]:
    years = [int(year) for year in ndb.years]
    summary = [
        {
            "year": year,
            "source": ndb.sources[year],
            "background_db": ndb.background_databases[year],
            "output_db": ndb.database_names[year],
        }
        for year in years
    ]

    mapping_reports: dict[int, dict[str, Any] | None] = {}
    for year in years:
        if ndb.sources.get(year) != "energy_charts":
            mapping_reports[year] = None
            continue
        report = ndb.mapping_report(year)
        mapping_reports[year] = (
            _table_payload(report) if getattr(report, "empty", True) is False else None
        )

    table_previews: dict[int, dict[str, Any]] = {}
    column_sums: dict[int, dict[str, float]] = {}
    for year in years:
        table = ndb.table(year)
        preview = table.head(_PREVIEW_ROW_LIMIT)
        table_previews[year] = _table_payload(preview)
        column_sums[year] = {
            str(column): float(table[column].sum()) for column in table.columns
        }

    gap_warnings = [
        message
        for message in warnings
        if "mapping gap" in message.lower() or "fallback" in message.lower()
    ]

    return {
        "years": years,
        "summary": summary,
        "mapping_reports": mapping_reports,
        "table_previews": table_previews,
        "column_sums": column_sums,
        "warnings": warnings,
        "gap_warnings": gap_warnings,
        "log": [f"Create completed for years: {years}"],
    }


def _default_new_database(**kwargs):
    from shrecc.pipeline import NewDatabase

    return NewDatabase(**kwargs)


def _table_payload(frame: Any) -> dict[str, Any]:
    index_name = frame.index.name or "activity"
    columns = [str(index_name), *[str(column) for column in frame.columns]]
    rows = []
    for index_value, row in frame.iterrows():
        rows.append([str(index_value), *[float(row[column]) for column in frame.columns]])
    return {"columns": columns, "rows": rows}
