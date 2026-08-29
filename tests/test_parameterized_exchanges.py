"""Rebuild Brightway parameterized-flow index; Parameterized Flows table follows the index."""

from bw2data.parameters import ActivityParameter, ParameterizedExchange
from bw2data.tests import bw2test

import bw2data as bd

from activity_browser.bwutils.parameters.formula_exchanges import (
    rebuild_parameterized_flow_index,
)
from fixtures.basic import DATABASE
from fixtures.bw_helpers import write_functional_database


@bw2test
def test_rebuild_indexes_small_database_constant_formula():
    write_functional_database("basic", DATABASE, process=True)
    rebuild_parameterized_flow_index("basic")

    rows = list(ParameterizedExchange.select())
    assert [row.formula for row in rows] == ["5+5"]
    assert ActivityParameter.select().where(ActivityParameter.database == "basic").count() >= 1
    process = bd.get_activity(("basic", "process"))
    bio = next(exc for exc in process.exchanges() if exc.get("formula") == "5+5")
    assert bio["amount"] == 10


EV_CASE = {
    ("ev", "elementary"): {
        "name": "elementary",
        "code": "elementary",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("ev", "car_prod"): {
        "name": "transport",
        "code": "car_prod",
        "location": "GLO",
        "type": "product",
        "unit": "km",
        "processor": ("ev", "car"),
    },
    ("ev", "car"): {
        "name": "transport, passenger car, electric",
        "code": "car",
        "location": "GLO",
        "type": "process",
        "exchanges": [
            {"type": "production", "amount": 1, "input": ("ev", "car_prod")},
            {
                "type": "biosphere",
                "amount": 0.0,
                "input": ("ev", "elementary"),
                "formula": "battery_size",
            },
        ],
    },
}


@bw2test
def test_rebuild_indexes_database_parameter_formulas_and_recalculates():
    write_functional_database("ev", EV_CASE, process=True)
    bd.parameters.new_database_parameters(
        [{"name": "battery_size", "amount": 0.00262, "formula": ""}],
        "ev",
    )
    ActivityParameter.delete().where(ActivityParameter.database == "ev").execute()
    ParameterizedExchange.delete().execute()
    assert ActivityParameter.select().count() == 0
    assert ParameterizedExchange.select().count() == 0

    rebuild_parameterized_flow_index("ev")

    assert ActivityParameter.select().where(ActivityParameter.database == "ev").count() >= 1
    rows = list(ParameterizedExchange.select())
    assert [row.formula for row in rows] == ["battery_size"]
    car = bd.get_activity(("ev", "car"))
    bio = next(exc for exc in car.exchanges() if exc.get("formula") == "battery_size")
    assert bio["amount"] == 0.00262


@bw2test
def test_rebuild_leaves_existing_parameters_in_place():
    from bw2data.parameters import DatabaseParameter, ProjectParameter

    write_functional_database("ev", EV_CASE, process=True)
    bd.parameters.new_project_parameters(
        [{"name": "proj_k", "amount": 1.5, "formula": ""}]
    )
    bd.parameters.new_database_parameters(
        [{"name": "battery_size", "amount": 0.00262, "formula": ""}],
        "ev",
    )
    car = bd.get_activity(("ev", "car"))
    bd.parameters.new_activity_parameters(
        [{
            "name": "user_share",
            "amount": 0.8,
            "formula": "",
            "database": "ev",
            "code": "car",
        }],
        str(car.id),
    )

    rebuild_parameterized_flow_index("ev")

    assert ProjectParameter.get(name="proj_k").amount == 1.5
    assert DatabaseParameter.get(name="battery_size").amount == 0.00262
    assert ActivityParameter.get(name="user_share").amount == 0.8
    assert ParameterizedExchange.select().count() == 1


@bw2test
def test_rebuild_skips_over_cap_without_parameters(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.parameters.formula_exchanges.INDEX_FLOW_CAP",
        0,
    )
    write_functional_database("basic", DATABASE, process=True)
    rebuild_parameterized_flow_index("basic")
    assert ParameterizedExchange.select().count() == 0


@bw2test
def test_rebuild_runs_over_cap_when_database_has_parameters(monkeypatch):
    monkeypatch.setattr(
        "activity_browser.bwutils.parameters.formula_exchanges.INDEX_FLOW_CAP",
        0,
    )
    write_functional_database("ev", EV_CASE, process=True)
    bd.parameters.new_database_parameters(
        [{"name": "battery_size", "amount": 0.00262, "formula": ""}],
        "ev",
    )
    rebuild_parameterized_flow_index("ev")
    assert ParameterizedExchange.select().count() == 1


@bw2test
def test_rebuild_replaces_stale_index_ids_on_rewrite():
    from bw2data.backends import ExchangeDataset

    write_functional_database("basic", DATABASE, process=True)
    rebuild_parameterized_flow_index("basic")
    live = ParameterizedExchange.select().first()
    ParameterizedExchange(
        group=live.group, exchange=999_999_999, formula="stale"
    ).save()
    assert ParameterizedExchange.select().count() == 2

    write_functional_database("basic", DATABASE, process=True)
    rebuild_parameterized_flow_index("basic")

    ids = [row.exchange for row in ParameterizedExchange.select()]
    assert 999_999_999 not in ids
    assert len(ids) == 1
    exc = ExchangeDataset.get_by_id(ids[0])
    assert exc.output_database == "basic"
    assert (exc.data or {}).get("formula") == "5+5"


@bw2test
def test_rebuild_indexes_production_and_technosphere_formulas():
    data = {
        ("mix", "elementary"): {
            "name": "elementary",
            "code": "elementary",
            "unit": "kg",
            "type": "emission",
            "categories": ("air",),
        },
        ("mix", "steel_prod"): {
            "name": "steel",
            "code": "steel_prod",
            "location": "GLO",
            "type": "product",
            "unit": "kg",
            "processor": ("mix", "steel"),
        },
        ("mix", "steel"): {
            "name": "steel production",
            "code": "steel",
            "location": "GLO",
            "type": "process",
            "exchanges": [
                {"type": "production", "amount": 1, "input": ("mix", "steel_prod")},
            ],
        },
        ("mix", "car_prod"): {
            "name": "car",
            "code": "car_prod",
            "location": "GLO",
            "type": "product",
            "unit": "kg",
            "processor": ("mix", "car"),
        },
        ("mix", "car"): {
            "name": "car production",
            "code": "car",
            "location": "GLO",
            "type": "process",
            "exchanges": [
                {
                    "type": "production",
                    "amount": 0,
                    "input": ("mix", "car_prod"),
                    "formula": "1+1",
                },
                {
                    "type": "technosphere",
                    "amount": 0,
                    "input": ("mix", "steel_prod"),
                    "formula": "3+4",
                },
                {
                    "type": "biosphere",
                    "amount": 0,
                    "input": ("mix", "elementary"),
                    "formula": "5+5",
                },
            ],
        },
    }
    write_functional_database("mix", data, process=True)
    rebuild_parameterized_flow_index("mix")

    formulas = sorted(row.formula for row in ParameterizedExchange.select())
    assert formulas == ["1+1", "3+4", "5+5"]
    car = bd.get_activity(("mix", "car"))
    amounts = {
        exc.get("formula"): exc["amount"]
        for exc in car.exchanges()
        if exc.get("formula")
    }
    assert amounts == {"1+1": 2, "3+4": 7, "5+5": 10}


def _relabel_database(data: dict, old: str, new: str) -> dict:
    relabeled = {}
    for (db, code), ds in data.items():
        copied = dict(ds)
        copied["code"] = code
        if copied.get("processor"):
            proc_db, proc_code = copied["processor"]
            copied["processor"] = (new if proc_db == old else proc_db, proc_code)
        exchanges = []
        for exc in copied.get("exchanges", []):
            row = dict(exc)
            if row.get("input"):
                in_db, in_code = row["input"]
                row["input"] = (new if in_db == old else in_db, in_code)
            exchanges.append(row)
        if exchanges:
            copied["exchanges"] = exchanges
        relabeled[(new if db == old else db, code)] = copied
    return relabeled


@bw2test
def test_rebuild_keeps_index_rows_from_other_databases():
    write_functional_database("basic", DATABASE, process=True)
    rebuild_parameterized_flow_index("basic")
    write_functional_database("other", _relabel_database(DATABASE, "basic", "other"), process=True)
    rebuild_parameterized_flow_index("other")

    formulas_by_db = {}
    for row in ParameterizedExchange.select():
        from bw2data.backends import ExchangeDataset

        exc = ExchangeDataset.get_by_id(row.exchange)
        formulas_by_db.setdefault(exc.output_database, []).append(row.formula)

    assert formulas_by_db == {"basic": ["5+5"], "other": ["5+5"]}


@bw2test
def test_excel_importer_extra_sends_database_write(monkeypatch):
    from types import SimpleNamespace

    from activity_browser.bwutils.importers import ABExcelImporter
    from bw2data.signals import on_database_write

    received = []
    on_database_write.connect(
        lambda sender, name: received.append(name),
        weak=False,
    )
    monkeypatch.setattr(
        "bw2io.importers.base_lci.LCIImporter.write_database",
        lambda self, **kwargs: SimpleNamespace(name="excel_db"),
    )
    importer = ABExcelImporter.__new__(ABExcelImporter)
    result = ABExcelImporter.write_database(importer)

    assert received == ["excel_db"]
    assert result.name == "excel_db"


@bw2test
def test_parameters_in_scope_returns_empty_when_database_locked(monkeypatch):
    from peewee import OperationalError

    from activity_browser.bwutils.commontasks import parameters_in_scope

    def locked(*args, **kwargs):
        raise OperationalError("database is locked")

    monkeypatch.setattr(
        "activity_browser.bwutils.commontasks.refresh_node",
        locked,
    )
    assert parameters_in_scope(node=("basic", "process")) == {}
