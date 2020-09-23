# -*- coding: utf-8 -*-
from typing import Collection

import brightway2 as bw
from bw2data.backends.peewee import ActivityDataset, sqlite3_lci_db
from bw2data.errors import ValidityError
from bw2io.errors import StrategyError
from bw2io.strategies.generic import format_nonunique_key_error
from bw2io.utils import DEFAULT_FIELDS, activity_hash


def relink_exchanges_dbs(data: Collection, relink: dict) -> Collection:
    """Use this to relink exchanges during an actual import."""
    for act in data:
        for exc in act.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bw.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError("Cannot relink exchange '{}', key '{}' not found.".format(exc, new_key)
                                     ).with_traceback(e.__traceback__)
    return data


def relink_exchanges_bw2package(data: dict, relink: dict) -> dict:
    """Use this to relink exchanges during an BW2Package import."""
    for key, value in data.items():
        for exc in value.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bw.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError("Cannot relink exchange '{}', key '{}' not found.".format(exc, new_key)
                                     ).with_traceback(e.__traceback__)
    return data


def relink_exchanges_existing_db(db: bw.Database, other: bw.Database) -> None:
    """Relink exchanges after the database has been created/written.

    This means possibly doing a lot of sqlite update calls.
    """
    assert db.backend == "sqlite", "Relinking only allowed for SQLITE backends"
    assert other.backend == "sqlite", "Relinking only allowed for SQLITE backends"

    duplicates, candidates = {}, {}
    altered = 0

    for ds in other:
        key = activity_hash(ds, DEFAULT_FIELDS)
        if key in candidates:
            duplicates.setdefault(key, []).append(ds)
        else:
            candidates[key] = (ds['database'], ds['code'])

    with sqlite3_lci_db.transaction() as transaction:
        try:
            # Only do relinking on external biosphere/technosphere exchanges.
            for i, exc in enumerate(
                    exc for act in db for exc in act.exchanges()
                    if exc.get("type") in {"biosphere", "technosphere"} and exc.input[0] != db.name
            ):
                # Use the input activity to generate the hash.
                key = activity_hash(exc.input, DEFAULT_FIELDS)
                if key in duplicates:
                    raise StrategyError(format_nonunique_key_error(exc.input, DEFAULT_FIELDS, duplicates[key]))
                elif key in candidates:
                    exc["input"] = candidates[key]
                    altered += 1
                exc.save()
                if i % 10000 == 0:
                    # Commit changes every 10k exchanges.
                    transaction.commit()
        except (StrategyError, ValidityError) as e:
            print(e)
            transaction.rollback()
    # Process the database after the transaction is complete.
    #  this updates the 'depends' in metadata
    db.process()
    print("Finished relinking database, {} exchanges altered.".format(altered))
