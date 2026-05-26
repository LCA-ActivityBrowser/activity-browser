from copy import deepcopy
from importlib import reload
from loguru import logger

import pandas as pd
import pytest
import os

import bw2data as bd
from PySide6 import QtCore

import bw_functional as bf
from bw2data.parameters import ParameterizedExchange
from bw2data.tests import bw2test

os.environ["AB_SKIP_SETTINGS_ON_STARTUP"] = "1"
os.environ["AB_NO_SEARCHER"] = "1"


def write_functional_database(
    name: str,
    data: dict,
    *,
    process: bool = True,
    mark_dirty: bool = False,
) -> bf.FunctionalSQLiteDatabase:
    """Write a ``functional_sqlite`` database and register it in the project."""
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


def write_calculation_setup(name: str, setup: dict) -> None:
    """Register a calculation setup in the current project."""
    bd.calculation_setups[name] = deepcopy(setup)
    bd.calculation_setups.flush()


def register_parameter_setup(database_name: str, setup: dict) -> None:
    """
    Register activity parameters and parameterized exchanges from fixture data.

    ``setup`` must contain ``activity_parameters`` and ``parameterized_exchanges``.
    Each parameterized exchange entry uses ``process_code``, ``exchange_type``, and ``formula``.
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


@pytest.fixture
def no_exception_dialogs(monkeypatch):
    """Monkeypatch QMessageBox.critical to do nothing, to avoid blocking tests."""
    from qtpy import QtWidgets

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args, **kwargs: None)
    yield
    # No need to undo the monkeypatch, pytest does it automatically


@pytest.fixture
def main_window(qtbot, monkeypatch, no_exception_dialogs):
    """Return the main window of the application instance."""
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    # Reload modules to ensure a clean state for each test
    reload(metadata)
    reload(app.main)
    reload(app)
    metadata.dataframe = pd.DataFrame()

    app.main_window.show()

    yield main_window

    app.main_window.deleteLater()

    qtbot.wait(10)


@pytest.fixture
@bw2test
def basic_database(qapp, main_window):
    import time
    from activity_browser.app import metadata
    from fixtures.basic import CALCULATION_SETUP, DATABASE, METHOD

    qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

    i = 0
    while metadata.loader.secondary_status != "done" and i < 60:
        logger.warning("Waiting for project load to finish")
        time.sleep(1)
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
        i += 1

    db = write_functional_database("basic", DATABASE, process=False, mark_dirty=True)
    write_method("basic_method", METHOD, process=False)
    write_calculation_setup("basic_calculation_setup", CALCULATION_SETUP)

    i = 0
    while metadata.loader.secondary_status != "done" and i < 60:
        logger.warning("Waiting for database load to finish...")
        time.sleep(1)
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
        i += 1

    if i >= 60:
        raise TimeoutError("Metadata loader did not finish in time.")

    yield db


@pytest.fixture
@bw2test
def mc_project():
    """
    Minimal functional_sqlite project for Monte Carlo uncertainty tests.

    Yields the calculation setup name. Does not load the Activity Browser UI.
    """
    from fixtures.monte_carlo import (
        CALCULATION_SETUP,
        CALCULATION_SETUP_NAME,
        DATABASE,
        METHOD,
        METHOD_NAME,
    )

    write_functional_database("mc", DATABASE, process=True)
    write_method(METHOD_NAME, METHOD, process=True)
    write_calculation_setup(CALCULATION_SETUP_NAME, CALCULATION_SETUP)
    yield CALCULATION_SETUP_NAME


@pytest.fixture
@bw2test
def mc_project_with_parameters():
    """
    Like ``mc_project`` but with uncertain parameter ``bio_amount`` on the main biosphere exchange.
    """
    from fixtures.monte_carlo import (
        CALCULATION_SETUP,
        CALCULATION_SETUP_NAME,
        DATABASE_NAME,
        DATABASE_WITH_PARAMETER_FORMULA,
        METHOD,
        METHOD_NAME,
        PARAMETER_SETUP,
    )

    write_functional_database("mc", DATABASE_WITH_PARAMETER_FORMULA, process=True)
    register_parameter_setup(DATABASE_NAME, PARAMETER_SETUP)
    write_method(METHOD_NAME, METHOD, process=True)
    write_calculation_setup(CALCULATION_SETUP_NAME, CALCULATION_SETUP)
    yield CALCULATION_SETUP_NAME
