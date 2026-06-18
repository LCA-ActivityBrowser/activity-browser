from importlib import reload
from loguru import logger

import pandas as pd
import pytest
import os
import time

import bw2data as bd
from PySide6 import QtCore, QtWidgets

from bw2data.tests import bw2test

from fixtures.bw_helpers import (
    register_parameter_setup,
    write_calculation_setup,
    write_functional_database,
    write_method,
)

os.environ["AB_SKIP_SETTINGS_ON_STARTUP"] = "1"
os.environ["AB_NO_SEARCHER"] = "1"

_MAIN_WINDOW_READY = False


def _wait_for_loader(qapp, loader, timeout: float = 30.0) -> None:
    """Poll metadata loader with short sleeps instead of blocking 1s per iteration."""
    deadline = time.monotonic() + timeout
    while loader.secondary_status != "done" and time.monotonic() < deadline:
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
        time.sleep(0.05)
    if loader.secondary_status != "done":
        raise TimeoutError("Metadata loader did not finish in time.")


def _ensure_main_window() -> None:
    """Create the main window once per process; tests only reset lightweight state."""
    global _MAIN_WINDOW_READY
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    if _MAIN_WINDOW_READY:
        return

    reload(metadata)
    reload(app.main)
    reload(app)
    _MAIN_WINDOW_READY = True


def _reset_main_window(qtbot) -> None:
    """Close extra tabs opened during a test; keep the main window alive."""
    from activity_browser import app
    from activity_browser.ui import core

    qapp = QtWidgets.QApplication.instance()
    mw = getattr(app, "main_window", None)
    if mw is None or not core.qt_is_valid(mw):
        return

    central = mw.centralWidget()
    if central is not None and core.qt_is_valid(central):
        while central.count() > 1:
            index = central.count() - 1
            widget = central.widget(index)
            central.removeTab(index)
            if widget is not None and core.qt_is_valid(widget):
                widget.deleteLater()

    if qapp is not None:
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
    qtbot.wait(10)


@pytest.fixture
def no_exception_dialogs(monkeypatch):
    """Monkeypatch QMessageBox.critical to do nothing, to avoid blocking tests."""
    from qtpy import QtWidgets

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args, **kwargs: None)
    yield


@pytest.fixture
def main_window(qtbot, monkeypatch, no_exception_dialogs):
    """Return the main window of the application instance."""
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    _ensure_main_window()
    metadata.dataframe = pd.DataFrame()
    app.main_window.show()

    yield app.main_window

    _reset_main_window(qtbot)


@pytest.fixture
@bw2test
def basic_database(qapp, main_window):
    from activity_browser.app import metadata
    from fixtures.basic import CALCULATION_SETUP, DATABASE, METHOD

    qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
    _wait_for_loader(qapp, metadata.loader)

    db = write_functional_database("basic", DATABASE, process=False, mark_dirty=True)
    write_method("basic_method", METHOD, process=False)
    write_calculation_setup("basic_calculation_setup", CALCULATION_SETUP)

    _wait_for_loader(qapp, metadata.loader)
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
