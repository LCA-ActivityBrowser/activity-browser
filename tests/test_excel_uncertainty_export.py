"""Excel export must not write #NUM! for unused uncertainty NaN fields."""
from __future__ import annotations

import tempfile
from pathlib import Path

import bw2data as bd
import openpyxl
import pytest
import stats_arrays as sa
from bw2data.parameters import ActivityParameter, Group, parameters
from bw2data.tests import bw2test
from bw2io import create_core_migrations

from activity_browser.bwutils.exporters import write_lci_excel
from activity_browser.bwutils.importers import ABExcelImporter
from activity_browser.bwutils.uncertainty import EMPTY_UNCERTAINTY


def _uncertainty(**fields) -> dict:
    return {**EMPTY_UNCERTAINTY, **fields}


def _excel_error_cells(path: Path) -> list[tuple[int, int, object]]:
    """Return (row, col, value) for cells stored as Excel errors / #NUM formulas."""
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        errors = []
        for r_i, row in enumerate(wb.active.iter_rows(), start=1):
            for cell in row:
                val = cell.value
                if cell.data_type == "e":
                    errors.append((r_i, cell.column, val))
                elif isinstance(val, str) and "NUM" in val.upper():
                    errors.append((r_i, cell.column, val))
        return errors
    finally:
        wb.close()


def _setup_project_with_uncertainty() -> str:
    create_core_migrations()
    bio_name = bd.config.biosphere
    bio = bd.Database(bio_name)
    bio.register()
    bio.write({
        (bio_name, "co2"): {
            "name": "Carbon dioxide",
            "code": "co2",
            "database": bio_name,
            "unit": "kilogram",
            "type": "emission",
            "categories": ("air",),
            "exchanges": [],
        },
    })

    db_name = "uncert_db"
    lognormal = _uncertainty(
        **{"uncertainty type": sa.LognormalUncertainty.id, "loc": 0.0, "scale": 0.25},
    )
    triangular = _uncertainty(
        **{
            "uncertainty type": sa.TriangularUncertainty.id,
            "minimum": 0.5,
            "loc": 1.0,
            "maximum": 2.0,
        },
    )
    normal_bio = _uncertainty(
        **{"uncertainty type": sa.NormalUncertainty.id, "loc": 1.5, "scale": 0.1},
    )
    uniform = _uncertainty(
        **{
            "uncertainty type": sa.UniformUncertainty.id,
            "minimum": 0.1,
            "maximum": 0.9,
        },
    )

    db = bd.Database(db_name)
    db.register()
    db.write({
        (db_name, "a"): {
            "name": "process A",
            "code": "a",
            "database": db_name,
            "location": "GLO",
            "unit": "kg",
            "type": "process",
            "exchanges": [
                {"input": (db_name, "a"), "type": "production", "amount": 1.0},
                {
                    "input": (db_name, "b"),
                    "type": "technosphere",
                    "amount": 2.0,
                    **lognormal,
                },
                {
                    "input": (bio_name, "co2"),
                    "type": "biosphere",
                    "amount": 3.0,
                    **normal_bio,
                },
            ],
        },
        (db_name, "b"): {
            "name": "process B",
            "code": "b",
            "database": db_name,
            "location": "GLO",
            "unit": "kg",
            "type": "process",
            "exchanges": [
                {
                    "input": (db_name, "b"),
                    "type": "production",
                    "amount": 1.0,
                    **triangular,
                },
            ],
        },
    })

    Group.create(name="g_a", order=[])
    parameters.new_activity_parameters(
        [{
            "name": "share",
            "amount": 0.5,
            "database": db_name,
            "code": "a",
            **uniform,
        }],
        "g_a",
    )
    return db_name


@pytest.mark.skip(reason="Slow (~13s) bw2test Excel uncertainty roundtrip; run manually when needed")
@bw2test
def test_excel_uncertainty_export_has_no_num_errors_and_roundtrips():
    db_name = _setup_project_with_uncertainty()

    with tempfile.TemporaryDirectory() as tmp:
        path = write_lci_excel(db_name, str(Path(tmp) / "uncert.xlsx"))
        assert _excel_error_cells(path) == []

        target = "uncert_imported"
        importer = ABExcelImporter(str(path))
        importer.apply_basic_strategies()
        importer.apply_db_name(target)
        importer.apply_linking({})
        assert not list(importer.unlinked)
        importer.write_database(delete_existing=True, activate_parameters=True)

    by_type = {}
    for act in bd.Database(target):
        if act["name"] != "process A":
            continue
        for exc in act.exchanges():
            by_type[exc["type"]] = exc

    tech = by_type["technosphere"]
    assert tech["uncertainty type"] == sa.LognormalUncertainty.id
    assert tech["loc"] == 0.0
    assert tech["scale"] == 0.25

    bio = by_type["biosphere"]
    assert bio["uncertainty type"] == sa.NormalUncertainty.id
    assert bio["loc"] == 1.5
    assert bio["scale"] == 0.1

    prod = next(
        exc
        for act in bd.Database(target)
        if act["name"] == "process B"
        for exc in act.exchanges()
        if exc["type"] == "production"
    )
    assert prod["uncertainty type"] == sa.TriangularUncertainty.id
    assert prod["loc"] == 1.0
    assert prod["minimum"] == 0.5
    assert prod["maximum"] == 2.0

    param = ActivityParameter.get(
        (ActivityParameter.database == target) & (ActivityParameter.name == "share")
    )
    pdata = dict(param.dict)
    assert pdata.get("uncertainty type") == sa.UniformUncertainty.id
    assert pdata.get("minimum") == 0.1
    assert pdata.get("maximum") == 0.9
