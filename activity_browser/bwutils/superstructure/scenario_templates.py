"""Resolve and write calculation-setup scenario starter templates."""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from activity_browser.bwutils.utils import Parameters

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "scenarios"

EXAMPLE_SCENARIO_COLS = ("S1 example", "S2 example", "S3 example")


def scenario_template_path(kind: str, fmt: str) -> Path:
    """Return packaged starter path for ``kind`` in ``{'parameter','flow'}`` and ``fmt`` in ``{'xlsx','csv'}``."""
    if kind not in {"parameter", "flow"}:
        raise ValueError(f"Unknown template kind: {kind}")
    if fmt not in {"xlsx", "csv"}:
        raise ValueError(f"Unknown template format: {fmt}")
    name = "parameter-scenarios" if kind == "parameter" else "flow-scenarios"
    path = TEMPLATES_DIR / f"{name}.{fmt}"
    if not path.is_file():
        raise FileNotFoundError(f"Scenario template not found: {path}")
    return path


def project_has_parameters() -> bool:
    return bool(Parameters.from_bw_parameters())


def parameter_template_dataframe() -> pd.DataFrame:
    """Project parameters as a parameter-scenario table with empty example scenario columns."""
    data = [p[:3] for p in Parameters.from_bw_parameters()]
    df = pd.DataFrame(data, columns=["Name", "Group", "default"])
    for col in EXAMPLE_SCENARIO_COLS:
        df[col] = pd.NA
    return df


def write_parameter_template(path: Path, df: pd.DataFrame | None = None) -> None:
    """Write a parameter-scenario template to ``path`` (.xlsx or .csv)."""
    path = Path(path)
    table = parameter_template_dataframe() if df is None else df
    if path.suffix.lower() == ".csv":
        table.to_csv(path, index=False, sep=";")
    else:
        if path.suffix.lower() not in {".xlsx", ".xls"}:
            path = path.with_suffix(".xlsx")
        table.to_excel(path, index=False)


def copy_scenario_template(kind: str, fmt: str, destination: Path) -> Path:
    """Copy a packaged empty starter to ``destination`` (suffix forced to match ``fmt``)."""
    source = scenario_template_path(kind, fmt)
    destination = Path(destination)
    if destination.suffix.lower() != f".{fmt}":
        destination = destination.with_suffix(f".{fmt}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination
