"""Brightway write helpers shared by pytest fixtures and setup scripts."""

from __future__ import annotations

from copy import deepcopy

import bw2data as bd
import bw_functional as bf
from bw2data.parameters import ParameterizedExchange


def write_functional_database(
    name: str,
    data: dict,
    *,
    process: bool = True,
    mark_dirty: bool = False,
) -> bf.FunctionalSQLiteDatabase:
    """Write a ``functional_sqlite`` database and register it in the current project."""
    db = bf.FunctionalSQLiteDatabase(name)
    db.write(deepcopy(data), process=process)
    if mark_dirty:
        db.metadata["dirty"] = True
    bd.databases.flush()
    return db


def write_method(
    name: str,
    cfs: list,
    *,
    unit: str = "kilogram",
    process: bool = True,
) -> None:
    """Register and write an LCIA method."""
    method = bd.Method((name,))
    method.register(unit=unit, num_cfs=len(cfs))
    method.write(deepcopy(cfs), process=process)
    bd.methods.flush()


def write_calculation_setup(name: str, setup: dict) -> None:
    """Register a calculation setup in the current project."""
    bd.calculation_setups[name] = deepcopy(setup)
    bd.calculation_setups.flush()


def register_parameter_setup(database_name: str, setup: dict) -> None:
    """
    Register activity parameters and parameterized exchanges from fixture data.

    ``setup`` must contain ``activity_parameters`` and ``parameterized_exchanges``.
    """
    process_groups: dict[str, str] = {}

    for row in setup["activity_parameters"]:
        param_row = deepcopy(row)
        process_code = param_row["code"]
        process = bd.get_activity((database_name, process_code))
        group = str(process.id)
        process_groups[process_code] = group
        bd.parameters.new_activity_parameters([param_row], group)

    for spec in setup["parameterized_exchanges"]:
        process_code = spec["process_code"]
        group = process_groups[process_code]
        process = bd.get_activity((database_name, process_code))
        exchange = next(
            exc
            for exc in process.exchanges()
            if exc.get("type") == spec["exchange_type"]
        )
        ParameterizedExchange(
            group=group,
            exchange=exchange.id,
            formula=spec["formula"],
        ).save()

    bd.parameters.recalculate()
