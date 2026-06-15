from copy import deepcopy
from importlib import reload
from loguru import logger

import pandas as pd
import pytest
import os

import bw2data as bd
from PySide6 import QtCore

from bw2data.tests import bw2test

from fixtures.bw_helpers import (
    register_parameter_setup,
    write_calculation_setup,
    write_functional_database,
    write_method,
)

os.environ["AB_SKIP_SETTINGS_ON_STARTUP"] = "1"
os.environ["AB_NO_SEARCHER"] = "1"


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

    yield app.main_window

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
def lcia_overview_project():
    """LCIA overview test database and calculation setups (1×1 … 10×10, MC)."""
    from fixtures.lcia_overview import (
        CALCULATION_SETUPS,
        DATABASE_NAME,
        DATABASE,
        METHODS,
    )

    write_functional_database(DATABASE_NAME, DATABASE, process=True)
    for method_key, cfs in METHODS.items():
        write_method(method_key, cfs, process=True)
    for cs_name, setup in CALCULATION_SETUPS.items():
        write_calculation_setup(cs_name, setup)
    yield DATABASE_NAME


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
