"""Helpers for database export/import round-trip tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import bw2data as bd
from bw2io.strategies import normalize_units as normalize_unit_fields

from activity_browser.bwutils.exporters import store_database_as_package, write_lci_excel
from activity_browser.bwutils.importers import ABExcelImporter, ABPackage

SKIP_ACT_KEYS = {"id", "worksheet name"}
SKIP_EXC_KEYS = {"id", "output", "original_amount"}
# ``original_amount`` is Brightway bookkeeping when a formula is present (fallback if
# the formula is removed). Excel re-import adds it; in-memory API setup may not. We
# still compare ``amount`` and ``formula`` — this skip is only for round-trip tests.
DENORMALIZED_EXC_KEYS = {
    "name", "database", "unit", "location", "categories",
    "reference product", "product",
}


def functional_data(db_name: str, *, parameters: bool = False) -> dict:
    fuel_product, fuel_process = "fuel_prod", "fuel_proc"
    elec_product, elec_process = "elec_prod", "elec_proc"
    fuel_exchanges = [{"type": "production", "amount": 1, "input": (db_name, fuel_product)}]
    if parameters:
        fuel_exchanges.append(
            {"type": "technosphere", "amount": 0.5, "input": (db_name, elec_product)},
        )
    return {
        (db_name, fuel_product): {
            "name": "fuel product", "code": fuel_product, "location": "GLO",
            "type": "product", "unit": "liter", "processor": (db_name, fuel_process),
        },
        (db_name, fuel_process): {
            "name": "fuel production", "code": fuel_process, "location": "GLO",
            "type": "process",
            "exchanges": fuel_exchanges,
        },
        (db_name, elec_product): {
            "name": "electricity product", "code": elec_product, "location": "GLO",
            "type": "product", "unit": "kWh", "processor": (db_name, elec_process),
        },
        (db_name, elec_process): {
            "name": "electricity production", "code": elec_process, "location": "GLO",
            "type": "process",
            "exchanges": [{"type": "production", "amount": 1, "input": (db_name, elec_product)}],
        },
    }


def sqlite_data(db_name: str) -> dict:
    return {
        (db_name, "process_a"): {
            "name": "process A", "code": "process_a", "location": "GLO",
            "unit": "kg", "type": "process",
            "exchanges": [{"type": "production", "amount": 1, "input": (db_name, "process_a")}],
        },
        (db_name, "process_b"): {
            "name": "process B", "code": "process_b", "location": "GLO",
            "unit": "kg", "type": "process",
            "exchanges": [
                {"type": "production", "amount": 1, "input": (db_name, "process_b")},
                {"type": "technosphere", "amount": 0.5, "input": (db_name, "process_a")},
            ],
        },
    }


def parameter_setup(db_name: str, *, process_code: str = "process_b") -> dict:
    exchange_type = "technosphere"
    return {
        "activity_parameters": [{
            "name": "share", "amount": 0.5, "formula": "",
            "database": db_name, "code": process_code,
        }],
        "parameterized_exchanges": [{
            "process_code": process_code, "exchange_type": exchange_type, "formula": "share",
        }],
    }


def write_source_db(name: str, kind: str, *, parameters: bool = False) -> None:
    from fixtures.bw_helpers import register_parameter_setup, write_functional_database

    if kind == "functional":
        write_functional_database(
            name, functional_data(name, parameters=parameters), process=True,
        )
        if parameters:
            register_parameter_setup(name, parameter_setup(name, process_code="fuel_proc"))
    else:
        db = bd.Database(name)
        db.register()
        db.write(deepcopy(sqlite_data(name)), process=True)
        if parameters:
            register_parameter_setup(name, parameter_setup(name))


def import_excel(path: str, target_db: str) -> None:
    importer = ABExcelImporter(path)
    importer.apply_basic_strategies()
    importer.apply_db_name(target_db)
    importer.apply_linking({})
    importer.write_database(delete_existing=True)


def roundtrip_import(source: str, fmt: str, tmp: str) -> str:
    target = f"{source}_imported"
    if fmt == "excel":
        import_excel(str(write_lci_excel(source, str(Path(tmp) / "db.xlsx"))), target)
    else:
        pkg = Path(tmp) / f"{source}.bw2package"
        store_database_as_package(source, str(pkg))
        ABPackage.import_file(str(pkg), rename=target, relink={})
    return target


def _norm_key(key, source_db: str, target_db: str):
    if isinstance(key, tuple) and len(key) == 2 and key[0] == target_db:
        return (source_db, key[1])
    return key


def _normalize_unit(unit: str | None) -> str | None:
    return None if unit is None else normalize_unit_fields([{"unit": unit}])[0]["unit"]


def activity_semantics(act, source_db: str, target_db: str) -> dict:
    data = {k: v for k, v in dict(act).items() if k not in SKIP_ACT_KEYS}
    data["database"] = source_db
    if data.get("processor"):
        data["processor"] = _norm_key(data["processor"], source_db, target_db)
    if "unit" in data:
        data["unit"] = _normalize_unit(data["unit"])
    if data.get("product") is None and data.get("reference product"):
        data["product"] = data["reference product"]
    exchanges = []
    for exc in act.exchanges():
        row = {k: v for k, v in dict(exc).items() if k not in SKIP_EXC_KEYS | DENORMALIZED_EXC_KEYS}
        if "input" in row:
            row["input"] = _norm_key(row["input"], source_db, target_db)
        if "unit" in row:
            row["unit"] = _normalize_unit(row["unit"])
        exchanges.append(row)
    data["exchanges"] = sorted(exchanges, key=lambda e: json.dumps(e, sort_keys=True, default=str))
    return data


def compare_databases_semantically(source_db: str, target_db: str) -> list[str]:
    source = {a["code"]: activity_semantics(a, source_db, target_db) for a in bd.Database(source_db)}
    target = {a["code"]: activity_semantics(a, source_db, target_db) for a in bd.Database(target_db)}
    issues = []
    if set(source) != set(target):
        issues.append(f"code sets differ: source-only={set(source) - set(target)} target-only={set(target) - set(source)}")
    for code in sorted(set(source) & set(target)):
        if source[code] != target[code]:
            issues.append(f"activity {code!r} differs semantically")
    if bd.databases[source_db].get("backend") != bd.databases[target_db].get("backend"):
        issues.append("database backend differs")
    return issues


def visible_product_count(db_name: str) -> int:
    processors = {act.get("processor") for act in bd.Database(db_name) if act.get("processor")}
    return sum(1 for act in bd.Database(db_name) if act.key not in processors)
