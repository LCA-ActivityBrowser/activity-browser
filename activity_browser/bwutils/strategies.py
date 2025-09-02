# -*- coding: utf-8 -*-
import hashlib
import json
from typing import Collection
from logging import getLogger

from bw2io.errors import StrategyError
from bw2io.strategies.generic import (format_nonunique_key_error,
                                      link_iterable_by_fields)
from bw2io.utils import DEFAULT_FIELDS, activity_hash

import bw2data as bd
from bw2data.backends import ActivityDataset, sqlite3_lci_db

from ..bwutils.errors import ExchangeErrorValues
from .commontasks import clean_activity_name

log = getLogger(__name__)

TECHNOSPHERE_TYPES = {"technosphere", "substitution", "production"}
BIOSPHERE_TYPES = {"economic", "emission", "natural resource", "social"}

RELINK_FIELDS = (
    "name",
    "database",
    "categories",
    "unit",
    "reference product",
    "location",
)


def relink_exchanges_dbs(data: Collection, relink: dict) -> Collection:
    """Use this to relink exchanges during an actual import."""
    for act in data:
        for exc in act.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bd.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError(
                        "Cannot relink exchange '{}', key '{}' not found.".format(
                            exc, new_key
                        )
                    ).with_traceback(e.__traceback__)
    return data


def relink_exchanges_with_db(data: list, old: str, new: str) -> list:
    if old == new:
        return _relink_exchanges(data, new)
    for act in data:
        for exc in (
            exc for exc in act.get("exchanges", []) if exc.get("database") == old
        ):
            exc["database"] = new
    return _relink_exchanges(data, new)


def link_exchanges_without_db(data: list, db: str) -> list:
    for act in data:
        for exc in (exc for exc in act.get("exchanges", []) if "database" not in exc):
            exc["database"] = db
    return _relink_exchanges(data, db)


def _relink_exchanges(data: list, other: str) -> list:
    other = bd.Database(other)
    if len(other) == 0:
        raise StrategyError("Cannot link to empty database")
    act = other.random()
    is_technosphere = act.get("type", "process") in ["process", "processwithreferenceproduct", "product"]
    kind = TECHNOSPHERE_TYPES if is_technosphere else BIOSPHERE_TYPES
    return link_iterable_by_fields(
        data, other=other, kind=kind, fields=RELINK_FIELDS, relink=True
    )


def relink_exchanges_bw2package(data: dict, relink: dict) -> dict:
    """Use this to relink exchanges during an BW2Package import."""
    for key, value in data.items():
        for exc in value.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bd.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError(
                        "Cannot relink exchange '{}', key '{}' not found.".format(
                            exc, new_key
                        )
                    ).with_traceback(e.__traceback__)
    return data


def rename_db_bw2package(data: dict, old: str, new: str) -> dict:
    """Replace the given `old` database name with the `new`."""

    def swap(x: tuple) -> tuple:
        return new if x[0] == old else x[0], x[1]

    new_data = {}
    keys = list(data.keys())
    for key in keys:
        value = data.pop(key)
        new_key = swap(key)
        if "database" in value and value["database"] == old:
            value["database"] = new
        for exc in value.get("exchanges", []):
            exc["input"] = swap(exc.get("input", ("", "")))
            exc["output"] = swap(exc.get("output", ("", "")))
        new_data[new_key] = value
    return new_data


def relink_exchanges(exchanges: list, candidates: dict, duplicates: dict) -> tuple:
    altered = 0
    remainder = 0
    unlinked_exchanges = {}
    with sqlite3_lci_db.transaction() as transaction:
        try:
            # Only do relinking on external biosphere/technosphere exchanges.
            for i, exc in exchanges:
                # Use the input activity to generate the hash.
                key = activity_hash(exc.input, DEFAULT_FIELDS)
                if key in duplicates:
                    raise StrategyError(
                        format_nonunique_key_error(
                            exc.input, DEFAULT_FIELDS, duplicates[key]
                        )
                    )
                elif key in candidates:
                    exc["input"] = candidates[key]
                    altered += 1
                else:
                    remainder += 1
                    if len(unlinked_exchanges) <= 5:
                        unlinked_exchanges[exc.input] = key
                exc.save()
                if i % 10000 == 0:
                    # Commit changes every 10k exchanges.
                    transaction.commit()
        except (StrategyError, bd.errors.ValidityError) as e:
            log.error(e)
            transaction.rollback()
    return (remainder, altered, unlinked_exchanges)


def relink_exchanges_existing_db(
    db: bd.Database, old: str, other: bd.Database
) -> tuple:
    """Relink exchanges after the database has been created/written.

    This means possibly doing a lot of sqlite update calls.
    """
    if old == other.name:
        log.info("No point relinking to same database.")
        return
    assert db.backend == "sqlite", "Relinking only allowed for SQLITE backends"
    assert other.backend == "sqlite", "Relinking only allowed for SQLITE backends"

    duplicates, candidates = {}, {}

    for ds in other:
        key = activity_hash(ds, DEFAULT_FIELDS)
        if key in candidates:
            duplicates.setdefault(key, []).append(ds)
        else:
            candidates[key] = ds.key

    exchanges = [
        (i, exc)
        for i, exc in enumerate(
            exc
            for act in db
            for exc in act.exchanges()
            if exc.get("type") in {"biosphere", "technosphere"} and exc.input[0] == old
        )
    ]

    # Process the database after the transaction is complete.
    #  this updates the 'depends' in metadata
    (remainder, altered, unlinked_exchanges) = relink_exchanges(
        exchanges, candidates, duplicates
    )
    db.process()
    log.info(
        "Relinked database '{}', {} exchange inputs changed from '{}' to '{}'.".format(
            db.name, altered, old, other.name
        )
    )
    return (remainder, altered, unlinked_exchanges)


def relink_activity_exchanges(act, old: str, other: bd.Database) -> tuple:
    if old == other.name:
        log.info("No point relinking to same database.")
        return
    db = bd.Database(act.key[0])
    assert db.backend == "sqlite", "Relinking only allowed for SQLITE backends"
    assert other.backend == "sqlite", "Relinking only allowed for SQLITE backends"

    duplicates, candidates = {}, {}

    for ds in other:
        key = activity_hash(ds, DEFAULT_FIELDS)
        if key in candidates:
            duplicates.setdefault(key, []).append(ds)
        else:
            candidates[key] = ds.key
    exchanges = [
        (i, e)
        for i, e in enumerate(
            exc
            for exc in act.exchanges()
            if exc.get("type") in {"technosphere", "biosphere"} and exc.input[0] == old
        )
    ]

    (remainder, altered, unlinked_exchanges) = relink_exchanges(
        exchanges, candidates, duplicates
    )
    db.process()
    log.info(
        "Relinked database '{}', {} exchange inputs changed from '{}' to '{}'.".format(
            db.name, altered, old, other.name
        )
    )
    return (remainder, altered, unlinked_exchanges)


def alter_database_name(data: list, old: str, new: str) -> list:
    """For ABExcelImporter, go through data and replace all instances
    of the `old` database name with `new`.
    """
    if old == new:
        return data  # Avoid doing any work if the two are equal.
    for ds in data:
        # Alter db on activities.
        ds["database"] = new
        for exc in ds.get("exchanges", []):
            # Note: this will only alter database if the field exists in the exchange.
            if exc.get("database") == old:
                exc["database"] = new
        for p, d in ds.get("parameters", {}).items():
            # Any parameters found here are activity parameters and we can
            # overwrite the database without issue.
            d["database"] = new
    return data


def hash_parameter_group(data: list) -> list:
    """For ABExcelImporter, go through `data` and change all the activity parameter
    `group` fields to use a md5 hash instead of the given group name.
    """
    for ds in (ds for ds in data if "parameters" in ds):
        key = (ds.get("database"), ds.get("code"))
        simple_hash = hashlib.md5(":".join(key).encode()).hexdigest()
        clean = clean_activity_name(ds.get("name"))
        for p, d in ds.get("parameters", {}).items():
            d["group"] = "{}_{}".format(clean, simple_hash)
    return data


def csv_rewrite_product_key(data):
    """Convert exchange 'product' key to a 'reference product' one."""
    for ds in data:
        for exc in (e for e in ds.get("exchanges", []) if "product" in e):
            exc["reference product"] = exc.pop("product")
    return data


def excel_error_detection(data: Collection):
    for ds in data:
        for exc in ds.get("exchanges", []):
            if "amount" not in exc:
                raise ExchangeErrorValues(
                    f"An Exception has occurred for activity {ds['name']}"
                    + "with errors in the exchange flows"
                )
    return data


def parse_JSON_fields(data: list) -> list:
    """Parse JSON fields in the data."""
    for ds in data:
        for key, value in ds.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                try:
                    ds[key] = json.loads(value)
                except json.JSONDecodeError:
                    continue
    return data
